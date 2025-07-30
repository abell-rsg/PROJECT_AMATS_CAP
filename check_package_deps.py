import sys
import yaml
from pathlib import Path
from collections import OrderedDict

import argparse

project_dir = Path(__file__).resolve().parent


class Environment(object):
    def __init__(self, yml_file, pkg_prj_switch=False):
        self.yml_file = yml_file
        self.pkg_prj = pkg_prj_switch
        self.pkg_pip_deps = self.pip_deps()

    @property
    def env_dict(self):
        """reads yml to a dictionary"""
        with open(self.yml_file, "r") as stream:
            return yaml.safe_load(stream)

    @property
    def env_name(self):
        """returns the name of the env"""
        return self.env_dict.get("name")

    @property
    def env_channels(self):
        """returns a list of channels"""
        return self.env_dict.get("channels")

    @property
    def env_dependencies(self):
        return self.env_dict.get("dependencies")

    @property
    def rp_package_deps(self):
        return self.env_dict.get("rp_dependencies")

    @property
    def conda_deps(self):
        """
        reads out the list of conda dependencies from environment.yml
        """
        return [
            item for item in self.env_dict.get("dependencies") if type(item) is not dict
        ]

    @property
    def local_packages(self):
        """
        reads an environment.yml for local packages and returns a list of package names
        """
        local = []
        for item in self.pip_deps:
            if item.startswith("-e"):
                pkg = item.split("/")[-1]
                local.append(pkg)
        return local

    def pip_deps(self):
        """
        checks an environment yaml for pip installs and returns a list
        of packages set in environment if any exist
        """
        deps = "dependencies"
        if self.pkg_prj:
            deps = "rp_dependencies"
        pip_dict = [
            item for item in self.env_dict.get(deps) if type(item) is dict
        ]
        if pip_dict:
            pip_dict = pip_dict[0]
            return pip_dict["pip"]
        else:
            return []

    def get_package_info(self):
        """
        searches an environment.yml for relative editable pip installs,
        return a dict of the environment.yml within the package
        """
        pip_deps = []
        conda_deps = []
        channels = []
        pkg_pip_deps = self.pip_deps()

        for item in pkg_pip_deps:
            # if a local package is specified, append its pip and conda deps
            if item.startswith("-e"):
                # get relative path
                relative_yml = item.split(" ")[1]
                yaml_data = Path(relative_yml, "environment.yml")
                # read yml to dict
                pkg_env = Environment(yml_file=yaml_data)
                # append any dependencies
                pkg_chans = [
                    chan for chan in pkg_env.env_channels if chan not in channels
                ]
                if pkg_chans:
                    channels += pkg_chans
                if pkg_env.pkg_pip_deps:
                    pkg_pips = [
                        pdeps for pdeps in pkg_env.pkg_pip_deps if pdeps not in pip_deps
                    ]
                    if pkg_pips:
                        pip_deps += pkg_pips
                pkg_cdeps = [
                    cdep for cdep in pkg_env.conda_deps if cdep not in conda_deps
                ]
                if pkg_cdeps:
                    conda_deps += pkg_cdeps
        return channels, conda_deps, pip_deps


def missing(list_a, list_b):
    return [item for item in list_b if item not in list_a]


def main(project_yml, prj_pkg_switch):

    project_env = Environment(yml_file=project_yml,
                              pkg_prj_switch=prj_pkg_switch)

    # generate list of conda and pip dependencies in project
    proj_channels = project_env.env_channels
    proj_conda_deps = project_env.conda_deps
    proj_pip_deps = project_env.pip_deps()

    # generate list of channels and dependencies (conda and pip) in local packages
    pkg_channels, pkg_conda_deps, pkg_pip_deps = project_env.get_package_info()

    # compare package list to project list and update project lists accordingly
    missing_channels = missing(list_a=proj_channels, list_b=pkg_channels)
    missing_conda = missing(list_a=proj_conda_deps, list_b=pkg_conda_deps)
    missing_pip = missing(list_a=proj_pip_deps, list_b=pkg_pip_deps)

    # update environment dictionary to include missing package dependencies
    proj_channels.extend(missing_channels)
    proj_conda_deps.extend(missing_conda)
    proj_pip_deps.extend(missing_pip)

    # update build environment with pkg values
    pip_dict = {"pip": proj_pip_deps}
    proj_conda_deps.append(pip_dict)
    build_environment = OrderedDict(
        name=project_env.env_name, channels=proj_channels, dependencies=proj_conda_deps
    )

    # write out new version of environment with package pips included
    with open("./build_environment.yml", "w") as build_yml:
        yaml.dump(dict(build_environment), build_yml)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--package', dest='package', default=False, action='store_true')
    args = parser.parse_args()

    if args.package:
        print('building package version of environment')
    else:
        print('building project version of environment')
    main(project_yml=Path(project_dir, "environment.yml"), prj_pkg_switch=args.package)
    # main(project_yml=Path(project_dir, "environment.yml"), prj_pkg_switch=True)
