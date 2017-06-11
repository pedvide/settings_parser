# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 13:33:57 2016

@author: Pedro
"""
# pylint: disable=E1101

#import sys
import logging
# nice debug printing of settings
import pprint
import copy
import warnings
from typing import Dict, Any, Union

import ruamel_yaml as yaml

from settings_parser.util import ConfigError, ConfigWarning, log_exceptions_warnings
from settings_parser.value import Value, DictValue
import settings_parser.settings_config as settings_config

class Settings(Dict):
    '''Contains all settings for the simulations,
        along with methods to load and validate settings files.'''

    def __init__(self, values_dict: Dict) -> None:  # pylint: disable=W0231
        self.dict_value = DictValue(copy.deepcopy(values_dict))

        namedvalue_list = self.dict_value.values_list

        self.needed_values = set(namedvalue.key for namedvalue in namedvalue_list
                                 if namedvalue.kind is Value.mandatory)
        self.optional_values = set(namedvalue.key for namedvalue in namedvalue_list
                                 if namedvalue.kind is Value.optional)
        self.exclusive_values = set(namedvalue.key for namedvalue in namedvalue_list
                                 if namedvalue.kind is Value.exclusive)
        self.optional_values = self.optional_values | self.exclusive_values

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
        if self.dict_value != other.dict_value:
            return False
        return True

    def __ne__(self, other: object) -> bool:
        '''Define a non-equality test'''
        if not isinstance(other, Settings):
            return NotImplemented
        return not self == other

    def __repr__(self) -> str:
        '''Representation of a settings instance.'''
        dict_value = repr(self.dict_value).replace('DictValue(', '', 1)
        dict_value = dict_value[:-1]
        return '{}({})'.format(self.__class__.__name__, dict_value)

    @log_exceptions_warnings
    def validate_all_values(self, file_dict: Dict) -> Dict:
        '''Validates the settings in the config_dict
            using the settings list.'''
#        pprint.pprint(file_cte)
        present_values = set(file_dict.keys())

        # if present values don't include all needed values
        if not present_values.issuperset(self.needed_values):
            raise ConfigError('Sections that are needed but not present in the file: ' +
                              str(self.needed_values - present_values) +
                              '. Those sections must be present!')

        set_extra = present_values - self.needed_values
        # if there are extra values and they aren't optional
        if set_extra and not set_extra.issubset(self.optional_values):
            warnings.warn('WARNING! The following values are not recognized:: ' +
                          str(set_extra - self.optional_values) +
                          '. Those values or sections should not be present', ConfigWarning)

        parsed_dict = self.dict_value.validate(file_dict)
        for key, value in parsed_dict.items():
            setattr(self, str(key), value)

#        pprint.pprint(parsed_dict)
        return parsed_dict

    @log_exceptions_warnings
    def validate(self, filename: str) -> None:
        ''' Load filename and extract the settings for the simulations
            If mandatory values are missing, errors are logged
            and exceptions are raised
            Warnings are logged if extra settings are found
        '''
        logger = logging.getLogger(__name__)
        logger.info('Reading settings file (%s)...', filename)

        # load file into config_cte dictionary.
        # the function checks that the file exists and that there are no errors
        file_cte = Loader().load_settings_file(filename)

        # store original configuration file
        with open(filename, 'rt') as file:
            self.config_file = file.read()

        self.parsed_settings = self.validate_all_values(file_cte)

        # log read and validated settings
        # use pretty print
        logger.debug('Settings dump:')
        logger.debug('File dict (config_cte):')
        logger.debug(pprint.pformat(file_cte))
        logger.debug('Validated dict (cte):')
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
                    file_dict = yaml.load(file)
            else:
                file_dict = yaml.load(filename)
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

#def load(filename: str, settings_dict: Dict) -> Settings:
#    '''Creates a new Settings instance and loads the configuration file.
#        Returns the Settings instance (dict-like).'''
#    settings = Settings()
#    settings.load(filename, settings_dict)
#    return settings


if __name__ == "__main__":
    settings = Settings(settings_config.settings)
    settings.validate('config_file.cfg')
