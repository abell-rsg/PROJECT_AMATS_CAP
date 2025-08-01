import numpy as np
import pandas as pd
import geopandas as gpd
import yaml
from thomas import copula
from thomas import normalize as normfuncs
from pathlib import Path
import itertools

# %% GLOBALS
config_yml = r"projects\PROJECT_AMATS_CAP\config.yml"
with open(config_yml) as stream:
    CONFIG = yaml.safe_load(stream)
NORM_MIN = 0.0
NORM_MAX = 100.0
OUT_DIR = Path(CONFIG["data_dir"], CONFIG["gis_folder"], "EquityIndices")


#%% HELPER FUNCTIONS
def percent(df, denom, numer, complement=False):
    # TODO: any divide by zero warning? 
    pct = df[numer] / df[denom]
    if complement:
        pct = 1 - pct
    return pct * 100

def density(df, denom, numer):
    return df[numer] / df[denom]

def normalize(df, col, max_val):
    norm = normfuncs.minmax(df[col])
    return norm * max_val

def generate_index(src_df, idx_name, idx_dict):
    choose_k = int(idx_dict["Choose"])
    idx_cols = idx_dict["Indicators"]
    constants = [c[:-1] for c in idx_cols if c[-1] == "*"]
    for_combo = [c for c in idx_cols if c[:-1] not in constants]
    idx_cols = constants + for_combo
    cop_df = src_df[idx_cols].fillna(0.0)
    combo_cops = []
    _src_df = src_df[idx_cols].copy()
    for combo in itertools.combinations(for_combo, choose_k):
        analysis_cols = constants + list(combo)
        cop_df = _src_df[analysis_cols].fillna(0.0)
        # Fit on the observations
        cop = copula.fit_nonparametric_gaussian_copula(cop_df[analysis_cols])
        # Apply to the observations + dummies
        dummy_rows = pd.DataFrame(
            data=[
                np.full((len(analysis_cols),), NORM_MIN),
                np.full((len(analysis_cols),), NORM_MAX)
            ],
            index=["MIN", "MAX"],
            columns=analysis_cols,
        )
        cop_df = pd.concat([cop_df, dummy_rows], axis=0)
        cop_df['cop_pctl'] = copula.nonparametric_gaussian_copula_cdf(
            cop, cop_df[analysis_cols]
        )
        # min/max normalize
        cop_df['cop_pctl'] = normfuncs.minmax(cop_df['cop_pctl'])
        # Write results, dropping dummies
        cop_df['combo'] = "-".join(combo)
        cop_df = cop_df.drop(["MIN", "MAX"])
        cop_df = cop_df[['cop_pctl', 'combo']].copy()
        cop_df.index.name = "GEOID"
        combo_cops.append(cop_df)

    cops_long = pd.concat([d.reset_index() for d in combo_cops]).reset_index()
    cmax = cops_long.groupby("GEOID").cop_pctl.max()
    cmax_row = cops_long.groupby("GEOID").cop_pctl.idxmax()
    idx_result = pd.DataFrame(
        data=cops_long.combo[cmax_row].values,
        index=cops_long.GEOID[cmax_row],
        columns=["max_combo"]
        )
    idx_result[idx_name] = cmax
    added_cols = ["cop_pctl", "combo"]
    keep_cols = [c for c in _src_df.columns if c not in added_cols]
    join_df = src_df[keep_cols]
    idx_result = idx_result.join(join_df)
    return idx_result


if __name__ == "__main__":
    acs_f = Path(OUT_DIR, "AMATS_ACS.pkl")
    cdc_f = Path(OUT_DIR, "AMATS_CDC.pkl")
    geos_f = Path(OUT_DIR, "AMATS_census_tracts.shp")
    acs_df = pd.read_pickle(acs_f)
    cdc_df = pd.read_pickle(cdc_f)
    geos = gpd.read_file(geos_f)
    cdc_specs = CONFIG["cdc_specs"]
    cdc_dict = CONFIG["Data"]["CDC"]
    cdc_data = cdc_specs.pop("data")
    cdc_all_vars = cdc_specs.pop("variables")

    # Merge tables
    cdc_for_merge = cdc_df.copy()
    drop_indices = [k for k in cdc_specs.keys()]
    drop_indices.append("year")
    cdc_for_merge.index = cdc_for_merge.index.droplevel(drop_indices)
    keep_cols = [k for k in cdc_dict.keys()]
    cdc_for_merge = cdc_for_merge[keep_cols].copy()
    cdc_for_merge.columns = keep_cols
    merge_df = acs_df.join(cdc_for_merge)
    merge_df = merge_df.merge(
        geos[["GEOID", "ALAND"]], left_index=True, right_on="GEOID"
    ).set_index("GEOID")

    # Estimate indicators (combos of variables)
    clean_cols = []
    for iname, ispecs in CONFIG["Indicators"].items():
        clean_cols.append(iname)
        imethod = ispecs.pop("method")
        if imethod == "None":
            continue
        callable = globals()[imethod] # TODO: move to src and import?
        iargs = ispecs["args"]
        if "complement" in iargs:
            ikwargs = {"complement": True}
            iargs.pop(-1)
        else:
            ikwargs = {}
        merge_df[iname] = callable(merge_df, *iargs, **ikwargs)
        norm = ispecs.get("normalize", False)
        if norm:
            merge_df[iname] = normalize(merge_df, iname, norm)
    
    index_src = merge_df[clean_cols].copy()

    # Estimate indices
    for idx_name, idx_dict in CONFIG["Indices"].items():
        # Apply index generation logic; join to geos; write output
        idx_estimates = generate_index(index_src, idx_name, idx_dict)
        idx_geo = geos.merge(
            idx_estimates, how='right', left_on="GEOID", right_index=True,
        )
        out_file = Path(OUT_DIR, f"{idx_name}.shp")
        idx_geo.to_file(out_file)