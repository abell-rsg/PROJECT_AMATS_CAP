from setuptools import find_packages, setup

with open('README.md', 'r') as readme:
    long_description = readme.read()

setup(
    name='amats_cap',
    package_dir={"": "src"},
    packages=find_packages('src'),
    version='0.0.0',
    description='Spatial analysis support for AMATS CAP',
    long_description=long_description,
    author='RSG, inc',
    license='Apache 2.0',
)