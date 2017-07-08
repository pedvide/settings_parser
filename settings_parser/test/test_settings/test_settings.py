# -*- coding: utf-8 -*-
"""
Created on Sat Oct 22 00:10:24 2016

@author: Villanueva
"""

import pytest
import os
import datetime

import settings_parser.settings as settings
from settings_parser.settings import Value, DictValue, Dict
from settings_parser.util import SettingsFileError, SettingsExtraValueWarning, SettingsValueError
from settings_parser.util import temp_filename

test_folder_path = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope='function')
def good_settings():

    cte_good = {'people': {'carmen': {'age': 28, 'city': 'ghent'},
                           'maria': {'age': 32, 'city': 'madrid'},
                           'pedro': {'age': 28, 'city': 'utrecht'},
                           'teresa': {'age': 34, 'city': 'madrid'}},
                'version': 1,
                'number': 3,
                'date1': datetime.date(2017, 6, 17),
                'date2': datetime.date(2017, 6, 17)
                 }
    return cte_good

@pytest.fixture(scope='function')
def settings_dict():
    return {'version': Value(int, val_min=1, val_max=1),
            'number': int,
            'people': Value(Dict[str, DictValue({'age': int, 'city': str})]),
            'date1': Value(datetime.date, expand_args=True),
            'date2': Value(datetime.date, expand_args=True)
           }


def test_good_config(good_settings, settings_dict):
    ''''Test that the returned Settings instance for a know config file is correct.'''
    filename = os.path.join(test_folder_path, 'test_standard_config.txt')
    sett = settings.Settings(settings_dict)
    sett.validate(filename)

    assert sett == good_settings
    assert sett.settings == good_settings

    good_settings['version'] = 2
    assert sett != good_settings


def test_change_config(settings_dict):
    ''''Changing the settings in any way gets updated.'''
    filename = os.path.join(test_folder_path, 'test_standard_config.txt')
    sett = settings.Settings(settings_dict)
    sett.validate(filename)

    sett.number = 5
    assert sett.number == sett['number']
    assert sett.number == sett.settings['number']

    sett['number'] = 10
    assert sett.number == sett['number']
    assert sett.number == sett.settings['number']

    sett.settings['number'] = 15
    assert sett.number == sett['number']
    assert sett.number == sett.settings['number']

    # add a different item
    sett.new_item = 'new'
    assert sett.new_item == sett['new_item']
    assert sett.new_item == sett.settings['new_item']


def test_non_existing_file(settings_dict):
    with pytest.raises(SettingsFileError) as excinfo:
        # load non existing file
        sett = settings.Settings(settings_dict)
        sett.validate(os.path.join(test_folder_path, 'test_non_existing_config.txt'))
    assert excinfo.match(r"Error reading file")
    assert excinfo.type == SettingsFileError

def test_empty_file(settings_dict):
    with pytest.raises(SettingsFileError) as excinfo:
        with temp_filename('') as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == SettingsFileError

@pytest.mark.parametrize('bad_yaml_data', [':', '\t', 'key: value:',
                                           'label1:\n    key1:value1'+'label2:\n    key2:value2'],
                          ids=['colon', 'tab', 'bad colon', 'bad value'])
def test_yaml_error_config(bad_yaml_data, settings_dict):
    with pytest.raises(SettingsFileError) as excinfo:
        with temp_filename(bad_yaml_data) as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"Error while parsing the config file")
    assert excinfo.type == SettingsFileError

def test_not_dict_config(settings_dict):
    with pytest.raises(SettingsFileError) as excinfo:
        with temp_filename('vers') as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"The settings file is empty or otherwise invalid")
    assert excinfo.type == SettingsFileError

def test_duplicate_key(settings_dict):
    data = '''key1: 5
key1: 10
'''
    with pytest.raises(SettingsValueError) as excinfo:
        with temp_filename(data) as filename:
            settings.Settings(settings_dict).validate(filename)
    assert excinfo.match(r"Duplicate label")
    assert excinfo.type == SettingsValueError


# test extra value in section lattice
def test_extra_value(settings_dict):
    extra_data = '''version: 1
extra: 3
'''
    with pytest.warns(SettingsExtraValueWarning) as record: # "extra_value" in lattice section
        with temp_filename(extra_data) as filename:
            settings.Settings({'version': settings_dict['version']}).validate(filename)
    assert len(record) == 2 # one warning
    warning = record.pop(SettingsExtraValueWarning)
    assert warning.category == SettingsExtraValueWarning
    assert 'Some values or sections should not be present in the file' in str(warning.message)

