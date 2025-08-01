from census import Census
from sodapy import Socrata
import pygris
import pandas as pd
import yaml
from six import string_types
from pathlib import Path


# %% GLOBALS
config_yml = r"projects\PROJECT_AMATS_CAP\config.yml"
with open(config_yml) as stream:
    CONFIG = yaml.safe_load(stream)
NORM_MIN = 0.0
NORM_MAX = 100.0
OUT_DIR = Path(CONFIG["data_dir"], CONFIG["gis_folder"], "EquityIndices")

#%% HELPER FUNCTIONS
def pull_acs(
        conn,
        product,
        data_dict,
        scale="state_county_tract",
        keep_raw=False,
        **kwargs
    ):
    prod_callable = getattr(conn, product)
    pull_method = getattr(prod_callable, scale)
    fetch_cols = ["NAME",]
    var_dfs = []
    for var, cols in data_dict.items():
        if type(cols) in string_types:
            cols = [cols]
        _fetch_cols = fetch_cols + cols
        acs_df = pd.DataFrame.from_records(
            pull_method(_fetch_cols, **kwargs)
        )
        geoid_cols = [c for c in acs_df.columns if c not in _fetch_cols]
        acs_df["GEOID"] = acs_df[geoid_cols].sum(axis=1)
        acs_df[var] = acs_df[cols].sum(axis=1)
        acs_df = acs_df.reset_index().set_index("GEOID")
        if keep_raw:
            var_dfs.append(acs_df)
        else:
            var_dfs.append(acs_df[[var]])
    combo_df = pd.concat(var_dfs, axis=1)
    return combo_df


def pull_cdc(
        conn,
        dataset,
        data_dict,
        values="data_value",
        keep_raw=False,
        **kwargs
    ):
    # values could include other reported values, like
    # low_confidence_limit, high_confidence_limit, totalpopulation, totalpop18plus
    _idx_cols = ["year", "stateabbr", "countyname", "locationid"]
    _group_cols = ["measure", "data_value_unit", "data_value_type"]
    cdc_dfs = []
    for var, cols in data_dict.items():
        if type(cols) in string_types:
            cols = [cols]
        var_dfs = []
        for col in cols:
            results = conn.get(
                dataset,
                measure=col,
                **kwargs
            )
            results_df = pd.DataFrame.from_records(results)
            piv_df = pd.pivot_table(
                data=results_df,
                values=values,
                index=_idx_cols,
                columns=_group_cols,
                aggfunc="first",
            )
            var_dfs.append(piv_df.astype(float))
        var_df = pd.concat(var_dfs, axis=1)
        # TODO: the sum is naive here but fine if there's only one column
        # used to represent `var`. Add support for more robuse combos of
        # columns?
        var_df[var] = var_df.sum(axis=1) 
        if keep_raw:
            cdc_dfs.append(var_df)
        else:
            cdc_dfs.append(var_df[[var]])
    combo_df = pd.concat(cdc_dfs, axis=1)
    return combo_df


if __name__ == "__main__":
    # Census connect
    c = Census(CONFIG["census_api"])
    acs_specs = CONFIG["acs_specs"]
    cprod = acs_specs["product"]
    cyear = acs_specs["year"]
    cstate = acs_specs["sfips"]
    ccty = acs_specs["cfips"]
    cvar_dir = acs_specs["var_url"].format(cyear, cprod)
    # c_var_lookup = pd.read_html(cvar_dir)[0]

    # pull census geo
    geo_callable = getattr(pygris, CONFIG["geo_scale"])
    geos = geo_callable(state=cstate, county=ccty)
    out_file = Path(OUT_DIR, "AMATS_census_tracts.shp")
    geos.to_file(out_file)

    # pull census data
    acs_df = pull_acs(
        conn=c,
        product=cprod,
        data_dict=CONFIG["Data"]["ACS"],
        scale="state_county_tract",
        state_fips=cstate,
        county_fips=ccty,
        tract=Census.ALL,
    )
    out_file = Path(OUT_DIR, "AMATS_ACS.pkl")
    acs_df.to_pickle(out_file)

    # CDC connect
    client=Socrata("data.cdc.gov", None)
    cdc_specs = CONFIG["cdc_specs"]
    cdc_data = cdc_specs.pop("data")
    cdc_dict = CONFIG["Data"]["CDC"]
    cdc_all_vars = cdc_specs.pop("variables")
    cdc_df = pull_cdc(
        conn=client,
        dataset=cdc_data,
        data_dict=cdc_dict,
        keep_raw=True,
        **cdc_specs
    )
    out_file = Path(OUT_DIR, "AMATS_CDC.pkl")
    cdc_df.to_pickle(out_file)

    
        



