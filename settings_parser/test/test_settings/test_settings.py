# -*- coding: utf-8 -*-
"""
Created on Sat Oct 22 00:10:24 2016

@author: Villanueva
"""

import pytest
import os

import settings_parser.settings as settings
from settings_parser.settings import Value, DictValue, Dict
from settings_parser.util import temp_filename

test_folder_path = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope='function')
def good_settings():

    cte_good = {'people': {'carmen': {'age': 28, 'city': 'ghent'},
                           'maria': {'age': 32, 'city': 'madrid'},
                           'pedro': {'age': 28, 'city': 'utrecht'},
                           'teresa': {'age': 34, 'city': 'madrid'}},
                'version': 1
                 }
    return cte_good

@pytest.fixture(scope='function')
def settings_dict():
    return {'version': Value(int, val_min=1, val_max=1),
            'people': Value(Dict[str, DictValue({'age': int, 'city': str})])
           }


def test_good_config(good_settings, settings_dict):
    ''''Test that the returned Settings instance for a know config file is correct.'''
    filename = os.path.join(test_folder_path, 'test_standard_config.txt')
    sett = settings.Settings(settings_dict)
    sett.validate(filename)

    assert sett.parsed_settings == good_settings

@pytest.mark.xfail
def test_settings_class(settings_dict):
    '''Test the creation, bool, and equality of Settings instances.'''

    settings1 = settings.Settings(settings_dict)
    settings2 = settings.Settings(settings_dict)
    assert settings1 == settings2

    settings_dict['version'] = 3
    settings3 = settings.Settings(settings_dict)
    assert settings3 != settings1


def test_non_existing_file(settings_dict):
    with pytest.raises(settings.ConfigError) as excinfo:
        # load non existing file
        sett = settings.Settings(settings_dict)
        sett.validate(os.path.join(test_folder_path, 'test_non_existing_config.txt'))
    assert excinfo.match(r"Error reading file")
    assert excinfo.type == settings.ConfigError

def test_empty_file(settings_dict):
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename('') as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == settings.ConfigError

@pytest.mark.parametrize('bad_yaml_data', [':', '\t', 'key: value:',
                                           'label1:\n    key1:value1'+'label2:\n    key2:value2'],
                          ids=['colon', 'tab', 'bad colon', 'bad value'])
def test_yaml_error_config(bad_yaml_data, settings_dict):
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename(bad_yaml_data) as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"Error while parsing the config file")
    assert excinfo.type == settings.ConfigError

def test_not_dict_config(settings_dict):
    with pytest.raises(settings.ConfigError) as excinfo:
        with temp_filename('vers') as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == settings.ConfigError

def test_version_config(settings_dict):
    with pytest.raises(ValueError) as excinfo:
        with temp_filename('version: 2') as filename:
            settings.Settings({'version': settings_dict['version']}).validate(filename)
    assert excinfo.match(r"cannot be larger than 1")
    assert excinfo.type == ValueError


# test extra value in section lattice
def test_extra_value(settings_dict):
    extra_data = '''version: 1
extra: 3
'''
    with pytest.warns(settings.ConfigWarning) as record: # "extra_value" in lattice section
        with temp_filename(extra_data) as filename:
            settings.Settings({'version': settings_dict['version']}).validate(filename)
    assert len(record) == 2 # one warning
    warning = record.pop(settings.ConfigWarning)
    assert warning.category == settings.ConfigWarning
    assert 'The following values are not recognized:: {\'extra\'}.' in str(warning.message)

