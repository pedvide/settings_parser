# -*- coding: utf-8 -*-
"""
Created on Sat Oct 22 00:10:24 2016

@author: Villanueva
"""

import pytest
import os

import settings_parser.settings as settings
from settings_parser.util import temp_filename

test_folder_path = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope='function')
def setup_cte():

    cte_good = {}


    return cte_good

@pytest.fixture(scope='function')
def setup_cte_full_S(setup_cte):
    copy_cte = {}
    return copy_cte

def test_standard_config(setup_cte):
    ''''Test that the returned Settings instance for a know config file is correct.'''
    filename = os.path.join(test_folder_path, 'test_standard_config.txt')
    cte = settings.load(filename)

    with open(filename, 'rt') as file:
        config_file = file.read()
    setup_cte['config_file'] = config_file
    settings_cte = settings.Settings(setup_cte)

    assert cte['lattice'] == settings_cte.lattice
    assert cte['states'] == settings_cte.states

    assert cte['excitations'] == settings_cte.excitations
    assert cte.decay['branching_S'] == settings_cte.decay['branching_S']
    assert cte.decay['decay_A'] == settings_cte.decay['decay_A']
    assert cte.decay['decay_S'] == settings_cte.decay['decay_S']
    assert cte.decay['branching_A'] == settings_cte.decay['branching_A']
    assert cte.decay == settings_cte.decay

    assert cte == settings_cte


def test_settings_class(setup_cte):
    '''Test the creation, bool, and equality of Settings instances.'''

    empty_settings = settings.Settings()
    assert not empty_settings

    settings1 = settings.Settings(setup_cte)
    settings2 = settings.Settings(setup_cte)
    assert settings1 == settings2

    setup_cte['lattice']['name'] = 'new_name'
    settings3 = settings.Settings(setup_cte)
    assert settings3 != settings1


def test_non_existing_file():
    with pytest.raises(settings.ConfigError) as excinfo:
        # load non existing file
        settings.load(os.path.join(test_folder_path, 'test_non_existing_config.txt'))
    assert excinfo.match(r"Error reading file")
    assert excinfo.type == settings.ConfigError

def test_empty_file():
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename('') as filename:
            settings.load(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == settings.ConfigError

@pytest.mark.parametrize('bad_yaml_data', [':', '\t', 'key: value:',
                                           'label1:\n    key1:value1'+'label2:\n    key2:value2'],
                          ids=['colon', 'tab', 'bad colon', 'bad value'])
def test_yaml_error_config(bad_yaml_data):
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename(bad_yaml_data) as filename:
            settings.load(filename)
    assert excinfo.match(r"Error while parsing the config file")
    assert excinfo.type == settings.ConfigError

def test_not_dict_config():
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename('vers') as filename:
            settings.load(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == settings.ConfigError

def test_version_config():
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename('version: 2') as filename:
            settings.load(filename)
    assert excinfo.match(r"Version number must be 1!")
    assert excinfo.type == settings.ConfigError


# test extra value in section lattice
def test_extra_value(recwarn):
    extra_data = '''version: 1
lattice:
    name: bNaYF4
    N_uc: 8
    # concentration
    S_conc: 0.3
    A_conc: 0.3
    # unit cell
    # distances in Angstrom
    a: 5.9738
    b: 5.9738
    c: 3.5297
    # angles in degree
    alpha: 90
    beta: 90
    gamma: 120
    # the number is also ok for the spacegroup
    spacegroup: P-6
    # info about sites
    sites_pos: [[0, 0, 0], [2/3, 1/3, 1/2]]
    sites_occ: [1, 1/2]
    extra_value: 3
states:
    sensitizer_ion_label: Yb
    sensitizer_states_labels: [GS, ES]
    activator_ion_label: Tm
    activator_states_labels: [3H6, 3F4, 3H5, 3H4, 3F3, 1G4, 1D2]
excitations:
    Vis_473:
        active: True
        power_dens: 1e6 # power density W/cm^2
        t_pulse: 1e-8 # pulse width, seconds
        process: Tm(3H6) -> Tm(1G4) # both ion labels are required
        degeneracy: 13/9
        pump_rate: 9.3e-4 # cm2/J
sensitizer_decay:
# lifetimes in s
    ES: 2.5e-3
activator_decay:
# lifetimes in s
    3F4: 12e-3
    3H5: 25e-6
    3H4: 2e-3
    3F3: 2e-6
    1G4: 760e-6
    1D2: 67.5e-6
sensitizer_branching_ratios:
activator_branching_ratios:
'''
    with pytest.warns(settings.ConfigWarning): # "extra_value" in lattice section
        with temp_filename(extra_data) as filename:
            settings.load(filename)
    assert len(recwarn) == 1 # one warning
    warning = recwarn.pop(settings.ConfigWarning)
    assert issubclass(warning.category, settings.ConfigWarning)
    assert 'Some values or sections should not be present in the file.' in str(warning.message)

