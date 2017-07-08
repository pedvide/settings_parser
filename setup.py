# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 16:17:59 2016

@author: Pedro
"""

# git tag -a v1.1 -m 'Version 1.1'
# git push origin --tags


# build with: python setup.py bdist_wheel sdist
# upload with: twine upload dist/* --skip-existing
# install locally with: pip install --upgrade --no-deps --force-reinstall dist\settings_parser-XXXX
# install from pypi with: pip install settings_parser

# CONDA:
# build and upload to pypi as before.
# then on directory python/conda delete folder settings_parser
# then conda skeleton pypi --setup-options="--single-version-externally-managed --record=record.txt" settings-parser
# conda build --py 3.6 settings_parser
# conda convert -f --platform all PATH-TO-PACKAGE -o .
# anaconda login
# anaconda upload */settings_parser-*

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
#from codecs import open
from os import path

from settings_parser import VERSION
from settings_parser import DESCRIPTION

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open('README.rst') as fd:
    long_description = fd.read()

setup(
    name='settings_parser',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=VERSION,

    description=DESCRIPTION,
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/pedvide/settings_parser',

    # Author details
    author='Pedro Villanueva Delgado',
    author_email='pedvide@gmail.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: User Interfaces',

        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.6',
    ],

    # What does your project relate to?
    keywords='settings configuration config validator parser',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['ruamel_yaml'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'test': ['pytest', 'pytest-cov', 'pytest-mock', 'pytest-xdist', 'pytest-catchlog',
                 'python-coveralls', 'flake8', 'mypy'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'settings_parser': [],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
#    data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
#    entry_points={
#        'console_scripts': [
#            'settings_parser = settings_parser.commandline:main',
#        ],
#    },
)
