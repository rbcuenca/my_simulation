from setuptools import find_packages
from setuptools import setup

setup(
    name='robcomp_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('robcomp_interfaces', 'robcomp_interfaces.*')),
)
