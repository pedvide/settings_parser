# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 13:33:57 2016

@author: Pedro
"""
# pylint: disable=E1101

from collections import OrderedDict
import re
#import sys
import logging
# nice debug printing of settings
import pprint
import os
import copy
import warnings
from typing import Dict, List, Any, Union

import yaml

from setting_parser.util import ConfigError, ConfigWarning, log_exceptions_warnings
from setting_parser.value import Value
import setting_parser.settings_config as configs

class Settings(Dict):
    '''Contains all settings for the simulations,
        along with methods to load and parse settings files.'''

    def __init__(self, cte_dict: Dict = None) -> None:  # pylint: disable=W0231

        if cte_dict is None:
            cte_dict = dict()
        else:
            # make own copy
            cte_dict = copy.deepcopy(cte_dict)

    def __getitem__(self, key: str) -> Any:
        '''Implements Settings[key].'''
        try:
            return getattr(self, key)
        except AttributeError as err:
            raise KeyError(str(err))

    def get(self, key: str, default: Any = None) -> Any:
        '''Implements settings.get(key, default).'''
        if key in self:
            return getattr(self, key)
        else:
            return default

    def __setitem__(self, key: str, value: Any) -> None:
        '''Implements Settings[key] = value.'''
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        '''Implements del Settings[key].'''
        delattr(self, key)

    def __contains__(self, key: Any) -> bool:
        '''Returns True if the settings contains the key'''
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __bool__(self) -> bool:
        '''Instance is True if all its data structures have been filled out'''
        for var in vars(self).keys():
#            print(var)
            # If the var is not literally False, but empty
            if getattr(self, var) is not False and not getattr(self, var):
                return False
        return True

    def __eq__(self, other: object) -> bool:
        '''Two settings are equal if all their attributes are equal.'''
        if not isinstance(other, Settings):
            return NotImplemented
        for attr in ['config_file', 'lattice', 'states', 'excitations', 'decay']:
            if self[attr] != other[attr]:
                return False
        return True

    def __ne__(self, other: object) -> bool:
        '''Define a non-equality test'''
        if not isinstance(other, Settings):
            return NotImplemented
        return not self == other

    def __repr__(self) -> str:
        '''Representation of a settings instance.'''
        return '''{}(lattice={},\n
states={},\n
excitations={},\n
decay={},\n
energy_transfer={})'''.format(self.__class__.__name__, pprint.pformat(self.lattice),
                              pprint.pformat(self.states), pprint.pformat(self.excitations),
                              pprint.pformat(self.decay), pprint.pformat(self.energy_transfer))

    @staticmethod
    @log_exceptions_warnings
    def parse_all_values(settings_list: List, config_dict: Dict) -> Dict:
        '''Parses the settings in the config_dict
            using the settings list.'''
#        pprint.pprint(config_dict)

        present_values = set(config_dict.keys())

        needed_values = set(val.name for val in settings_list if val.kind is Value.mandatory)
        optional_values = set(val.name for val in settings_list if val.kind is Value.optional)
        exclusive_values = set(val.name for val in settings_list if val.kind is Value.exclusive)
        optional_values = optional_values | exclusive_values

        # if present values don't include all needed values
        if not present_values.issuperset(needed_values):
            raise ConfigError('Sections that are needed but not present in the file: ' +
                              str(needed_values - present_values) +
                              '. Those sections must be present!')

        set_extra = present_values - needed_values
        # if there are extra values and they aren't optional
        if set_extra and not set_extra.issubset(optional_values):
            warnings.warn('WARNING! The following values are not recognized:: ' +
                          str(set_extra - optional_values) +
                          '. Those values or sections should not be present', ConfigWarning)

        parsed_dict = {}  # type: Dict
        for value in settings_list:
            name = value.name
            if value.kind is not Value.mandatory and (name not in config_dict or
                                                      config_dict[name] is None):
                continue
            value.name = name
            parsed_dict.update({name: value.parse(config_dict[name])})

#        pprint.pprint(parsed_dict)
        return parsed_dict

    @log_exceptions_warnings
    def load(self, filename: str) -> None:
        ''' Load filename and extract the settings for the simulations
            If mandatory values are missing, errors are logged
            and exceptions are raised
            Warnings are logged if extra settings are found
        '''
        logger = logging.getLogger(__name__)
        logger.info('Reading settings file (%s)...', filename)

        # load file into config_cte dictionary.
        # the function checks that the file exists and that there are no errors
        config_cte = Loader().load_settings_file(filename)

        # check version
        if 'version' not in config_cte or config_cte['version'] != 1:
            raise ConfigError('Error in configuration file ({})! '.format(filename) +
                              'Version number must be 1!')
        del config_cte['version']

        # store original configuration file
        with open(filename, 'rt') as file:
            self.config_file = file.read()

        self.parsed_settings = self.parse_all_values(configs.settings, config_cte)

        # log read and parsed settings
        # use pretty print
        logger.debug('Settings dump:')
        logger.debug('File dict (config_cte):')
        logger.debug(pprint.pformat(config_cte))
        logger.debug('Parsed dict (cte):')
        logger.debug(repr(self))

        logger.info('Settings loaded!')


class Loader():
    '''Load a settings file'''

    def __init__(self) -> None:
        '''Init variables'''
        self.file_dict = {}  # type: Dict

    @log_exceptions_warnings
    def load_settings_file(self, filename: Union[str, bytes], file_format: str = 'yaml',
                           direct_file: bool = False) -> Dict:
        '''Loads a settings file with the given format (only YAML supported at this time).
            If direct_file=True, filename is actually a file and not a path to a file.
            If the file doesn't exist ir it's emtpy, raise ConfigError.'''
        if file_format.lower() == 'yaml':
            self.file_dict = self._load_yaml_file(filename, direct_file)
        else:
            return NotImplemented

        if self.file_dict is None or not isinstance(self.file_dict, dict):
            msg = 'The settings file is empty or otherwise invalid ({})!'.format(filename)
            raise ConfigError(msg)

        return self.file_dict

    @log_exceptions_warnings
    def _load_yaml_file(self, filename: Union[str, bytes], direct_file: bool = False) -> Dict:
        '''Open a yaml filename and loads it into a dictionary
            ConfigError exceptions are raised if the file doesn't exist or is invalid.
            If direct_file=True, filename is actually a file and not a path to one
        '''
        file_dict = {}  # type: Dict
        try:
            if not direct_file:
                with open(filename) as file:
                    # load data as ordered dictionaries so the ET processes are in the right order
                    file_dict = self._ordered_load(file, yaml.SafeLoader)
            else:
                file_dict = self._ordered_load(filename, yaml.SafeLoader)
        except OSError as err:
            raise ConfigError('Error reading file ({})! '.format(filename) +
                              str(err.args)) from err
        except yaml.YAMLError as exc:
            msg = 'Error while parsing the config file: {}! '.format(filename)
            if hasattr(exc, 'problem_mark'):
                msg += str(exc.problem_mark).strip()
                if exc.context is not None:
                    msg += str(exc.problem).strip() + ' ' + str(exc.context).strip()
                else:
                    msg += str(exc.problem).strip()
                msg += 'Please correct data and retry.'
            else:  # pragma: no cover
                msg += 'Something went wrong while parsing the config file ({}):'.format(filename)
                msg += str(exc)
            raise ConfigError(msg) from exc

        return file_dict

    @staticmethod
    def _ordered_load(stream, YAML_Loader=yaml.Loader,  # type: ignore
                      object_pairs_hook=OrderedDict):
        '''Load data as ordered dictionaries so the ET processes are in the right order
        # not necessary any more, but still used
            http://stackoverflow.com/a/21912744
        '''

        class OrderedLoader(YAML_Loader):
            '''Load the yaml file use an OderedDict'''
            pass

        def no_duplicates_constructor(loader, node, deep=False):  # type: ignore
            """Check for duplicate keys."""
            mapping = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    msg = "Duplicate label {}!".format(key)
                    raise ConfigError(msg)
                value = loader.construct_object(value_node, deep=deep)
                mapping[key] = value

            # Load the yaml file use an OderedDict
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            no_duplicates_constructor)

        return yaml.load(stream, OrderedLoader)

def load(filename: str) -> Settings:
    '''Creates a new Settings instance and loads the configuration file.
        Returns the Settings instance (dict-like).'''
    settings = Settings()
    settings.load(filename)
    return settings


#if __name__ == "__main__":
#    import settings_parser.settings as settings
##    cte_std = settings.load('test/test_settings/test_standard_config.txt')
#    cte = settings.load('config_file.cfg')
