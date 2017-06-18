# -*- coding: utf-8 -*-
"""
Created on Sun Mar 12 13:16:47 2017

@author: Villanueva
"""


import sys
#import sys
# nice debug printing of settings
#import pprint
from typing import Dict, List, Tuple
from typing import Callable, TypeVar, Hashable, Any
from typing import Union, Sequence, Iterable, Mapping, Sized, Collection
from functools import wraps
from itertools import zip_longest
from enum import Enum
import warnings

from settings_parser.util import ConfigWarning, ValueTypeError
from settings_parser.util import no_logging, log_exceptions_warnings


## example on how to add a type to the typing module, in this case a OrderedDict
#import collections
#import typing
#class OrderedDictType(collections.OrderedDict, typing.MutableMapping[typing.KT, typing.VT],
#                      extra=collections.OrderedDict):
#    __slots__ = ()
#    def __new__(cls, *args, **kwds):
#        if typing._geqv(cls, OrderedDictType):
#            raise TypeError("Type OrderedDictType cannot be instantiated; "
#                            "use collections.OrderedDict() instead")
#        return typing._generic_new(collections.OrderedDict, cls, *args, **kwds)
#typing.OrderedDictType = OrderedDictType
#typing.OrderedDictType.__module__ = 'typing'

class Kind(Enum):
        mandatory = 1
        optional = 2
        exclusive = 3


# type of innermost type, could be int, list, etc
T = TypeVar('T')
# the type of the settings value is a type
ValType = type

class Value():
    '''A value of a setting. The value has an specific type and optionally max and min values.
        If the setting is a list, the list can have max and min length.
        The type can be nested, eg: a list of lists of ints; use the typing module for that:
        type=typing.List[typing.List[int]].
        If the setting is a nested sequence, the max and min length
        can be lists of the length of each list.
        At any level of the type tree a Union of types is allowed; if present, the leftmost type
        in the Union will be validated, if it doesn't succeed the next type will be validated etc.
        The innermost type must be concrete or a typing.Union of several concrete types.
        In this case the type of the settings will be checked agains in the values in the Union
        (in the same order) until one matches, or if none, an exception is raised.
        List accepts only one type, Tuple accepts any number of them to refer to
        tuples composed of those types.
        Fun is a function of one parameter that returns bool,
        the value to be validated will be passed to fun and for the validation to succeed
        it must return True.
        If expand_args is True, the value passed to validate will be expanded
        with **value if it's a dictionary and with *value otherwise.
        This allows using types that have several arguments, such as datetimes.'''

    mandatory = Kind.mandatory
    optional = Kind.optional
    exclusive = Kind.exclusive

    # len_max/min are ints b/c the length of a Sequence is always an int.
    def __init__(self, val_type: ValType, name: str = '',
                 val_max: T = None, val_min: T = None,
                 kind: Kind = Kind.mandatory,
                 fun: Callable[[T], bool] = None,
                 len_max: Union[int, List[int]] = None,
                 len_min: Union[int, List[int]] = None,
                 expand_args: bool = False) -> None:
        '''Val type can be a nested type (List[int], List[List[int]])'''

        self.name = name
        # val_type it's either a simple type, an Iterable or a Union
        # Nesting is possible
        self.val_type = val_type

        self.val_max = val_max
        self.val_min = val_min

        self.kind = kind
        self.fun = fun

        # convert to list
        self.len_max = [len_max] if not isinstance(len_max, Sequence) else len_max
        self.len_min = [len_min] if not isinstance(len_min, Sequence) else len_min

        self.expand_args = expand_args

    def __repr__(self) -> str:
        '''Return a representation of Value'''
        optional = ', '.join(attr + '=' + repr(getattr(self, attr))
                             for attr in ['name', 'val_max', 'val_min', 'len_max', 'len_min']
                             if getattr(self, attr) and getattr(self, attr) != [None])
        if self.kind is not Kind.mandatory:
            optional += ', kind=' + self.kind.name
        return '{}({}{})'.format(self.__class__.__name__, _clean_type_name(self.val_type),
                                 ', ' + optional if optional else '')

    def __call__(self, config_dict: Dict) -> Dict:
        '''Pretend to be a type so typing module doesn't complain'''
        return self.validate(config_dict)


    @staticmethod
    def _print_trace(value: T, val_type: ValType) -> None:  # pragma: no cover
        '''Print the current state of the tree parsing.'''
        type_name = _clean_type_name(val_type)
        print(value, type(value).__name__, type_name)

    @log_exceptions_warnings
    def _check_val_max_min(self, value: T) -> None:
        '''Check that the value is within the max and min values.'''
        # the type: ignore comments are there because it's possible that the user will
        # ask for an unorderable type but also give a max or min values.
        # That would fail, but that's the user's fault.
        msg1 = 'Value(s) of {} ({}) cannot be '.format(self.name or value, value)
        msg2 = '{} than {}.'
        try:
            if self.val_max is not None and value > self.val_max:  # type: ignore
                raise ValueError(msg1 + msg2.format('larger', self.val_max))
            if self.val_min is not None and value < self.val_min:  # type: ignore
                raise ValueError(msg1 + msg2.format('smaller', self.val_min))
        except TypeError as err:
            msg = ('Value {} of type {}'.format(value,_clean_type_name(type(value))) +
                   ' cannot be compared to ' +
                   ('val_max ({})'.format(self.val_max) if self.val_max else '') +
                   (' and/or ' if  self.val_max and  self.val_min else '') +
                   ('val_min ({})'.format(self.val_min) if self.val_min else '') +
                   '.')
            raise ValueTypeError(msg) from err

    @log_exceptions_warnings
    def _check_seq_len(self, seq: Sized, len_max: int, len_min: int) -> None:
        '''Checks that the sequence has the size given by self.len_max/min.'''
        msg1 = 'Length of {} ({}) cannot be '.format(self.name or seq, len(seq))
        msg2 = '{} than {}.'
        if len_max is not None and len(seq) > len_max:
            raise ValueError(msg1 + msg2.format('larger', len_max))
        if len_min is not None and len(seq) < len_min:
           raise ValueError(msg1 + msg2.format('smaller', len_min))

    def _wrong_type_error_msg(self, value: T, val_type: ValType) -> str:
        '''Return the error message because the type of the value is not the expected val_type.'''
        msg1 = 'Setting {} (value: {!r}, type: {}) does not '.format(self.name or value, value,
                                                                       type(value).__name__)
        msg2 = 'have the right type ({}).'.format(_clean_type_name(val_type))
        return msg1 + msg2

    def _cast_to_type(self, value: T, val_type: ValType) -> Any:
        '''Cast the value to the type, which should be callable.'''
        try:
            if self.expand_args:
                if isinstance(value, Dict):
                    parsed_value = val_type(**value)
                elif isinstance(value, Iterable):
                    parsed_value = val_type(*value)
                else:
                    raise ValueError('Expected a list or a dictionary.')
            else:
                parsed_value = val_type(value)
        except (ValueError, TypeError) as err:  # no match
            raise ValueError(self._wrong_type_error_msg(value, val_type) +
                             ' Details: "' + str(err).capitalize() + '".')
        else:
            # no exception, val_type matched the value!
            return parsed_value

    @staticmethod
    def trace(fn: Callable) -> Callable:  # pragma: no cover
        '''Trace the execution of a recursive function'''
        stream = sys.stdout
        indent_step = 2
        show_ret = False
        cur_indent = 0
        @wraps(fn)
        def wrapper(*args: Tuple, **kwargs: Dict) -> None:
            nonlocal cur_indent
            indent = ' ' * cur_indent
            argstr = ', '.join(
                [repr(a).replace('typing.', '') for a in args[1:3]])
            stream.write('%s%s(%s)\n' % (indent, fn.__name__, argstr))

            cur_indent += indent_step
            ret = fn(*args, **kwargs)
            cur_indent -= indent_step

            if show_ret:
                stream.write('%s--> %s\n' % (indent, ret))
            return ret
        return wrapper


    @log_exceptions_warnings
#    @trace
    def _validate_type_tree(self, value: T, val_type: ValType,
                            len_max: List = None, len_min: List = None,
                            key: bool = False) -> Any:
        '''Makes sure that the sequence/value has recursively the given type, ie:
            a = [1, 2, 3] has val_type=List, and then val_type=int
            b = [[1, 2, 3], [4, 5, 6]] has val_type=List, then val_type=List and val_type=int
            c = 1 has val_type=int.
            The innermost type has to be a concrete one (eg: int, str, etc) or an Union of
            concrete types; in this case each type in the Union will be tested in order.
            Returns the validated sequence/value.
            len_max/min is a list with the max and min list length at this and lower
            tree levels. The values can be None
        '''
        # Typing module types have an __extra__ attribute with the actual instantiable type,
        # ie: Tuple.__extra__ = tuple
        # Sequence types also have an __args__ attribute with a tuple of the inner type(s),
        # ie: List[int].__args__ = (int,)
        # Union types also have and __args__ attribute with the types of the union.
        # Same with Mappings
#        Value._print_trace(value, val_type)

        # length max and min at this tree level
        cur_len_max = None if not len_max else len_max[0]
        cur_len_min = None if not len_min else len_min[0]
        rest_len_max = [None] if len(len_max) < 1 else len_max[1:]
        rest_len_min = [None] if len(len_min) < 1 else len_min[1:]

        # Union type, try parsing each option until one works
        if type(val_type) == type(Union):  # pylint: disable=C0123
            type_list = val_type.__args__  # type: ignore
            for curr_type in type_list:
                try:
                    with no_logging():
                        parsed_value = self._validate_type_tree(value, curr_type, len_max, len_min)
                except ValueError as err:
                    # save exception and traceback for later
                    last_err = err
                    tb = sys.exc_info()[2]
                    continue
                else:
                    # some type in the Union matched
                    return parsed_value
            # no match, error
            msg = ('Setting {!r} (value: {!r}, type: {}) does not have '
                   'any of the right types ({})')
            msg = msg.format(self.name or value, value, type(value).__name__,
                             ', '.join(_clean_type_name(typ)
                                       for typ in val_type.__args__))  # type: ignore
            raise ValueError(msg + ', because ' + str(last_err)).with_traceback(tb)

        # generic mappings such as Dicts: validate both the keys and the values
        elif hasattr(val_type, '__extra__') and issubclass(val_type, Mapping):
            if not isinstance(value, Mapping):
                raise ValueError(self._wrong_type_error_msg(value, val_type) +
                                 ' Details: "This type can only validate dictionaries."')
            # go through all keys and values and validate them
            # __args__ has the two types for the keys and values
            key_type, values_type = val_type.__args__  # type: ignore
            mapping = {self._validate_type_tree(inner_key, key_type,
                                                rest_len_max, rest_len_min, key=True):
                       self._validate_type_tree(inner_val, values_type,
                                                rest_len_max, rest_len_min)
                       for inner_key, inner_val in value.items()}
            # check length
            self._check_seq_len(mapping, cur_len_max, cur_len_min)
            mapping_type = val_type.__extra__  # type: ignore
            return self._cast_to_type(mapping, mapping_type)

        # generic iterables such as Lists, Tuple, Sets: validate each item
        elif hasattr(val_type, '__extra__') and issubclass(val_type, Iterable):
            # first check that lst is of the right type
            # str behave like lists, so if the user wanted a list and value is a str,
            # cast_to_type will succeed! So avoid it,
            # also avoid iterating if value is not iterable
            if (isinstance(value, str) and not issubclass(val_type, str) or
                not isinstance(value, Collection)):
                raise ValueError(self._wrong_type_error_msg(value, val_type))

            elements_type = val_type.__args__   # type: ignore
            if elements_type is None:
                msg = 'Invalid requested type ({}), generic types must contain arguments.'
                raise ValueError(msg.format(_clean_type_name(val_type)))

            # build sequence from the lower branches,
            # pass the lower level lengths
            # if it´s a List, elements_type = (type, ), and zip_longest will iterate over
            # the list using the same type.
            # If it's Tuple, elements_type=(type1, type2, etc) and zip_longest will iterate over
            # each pair of inner_type and inner_value
            if type(val_type) == type(Tuple) and len(elements_type) != len(value):
                msg = ' Details: "Tuples must have the same number of sub-types and values."'
                raise ValueError(self._wrong_type_error_msg(value, val_type) + msg)
            sequence = [self._validate_type_tree(inner_value, inner_type,
                                                 rest_len_max, rest_len_min)
                        for inner_type, inner_value in zip_longest(elements_type, value,
                                                                   fillvalue=elements_type[0])]

            # check length
            self._check_seq_len(sequence, cur_len_max, cur_len_min)
            iterable_type = val_type.__extra__  # type: ignore
            return self._cast_to_type(sequence, iterable_type)

        # single concrete type (int, str, list, dict, ...): cast to correct type
        # DictValue also ends up here, casting a value to it calls DictValue's own validate method.
        elif not hasattr(val_type, '__extra__'):
            parsed_value = self._cast_to_type(value, val_type)
            # don't check if key is True: it's a mapping key
            if not key:
                self._check_val_max_min(parsed_value)

            if isinstance(parsed_value, Sized):
                self._check_seq_len(parsed_value, cur_len_max, cur_len_min)
            return parsed_value

        else:
            raise TypeError('Type not recognized or supported ({}).'.format(val_type))

    def validate(self, value: T) -> Any:
        '''validates the value from a settings file
            and tries to convert it to this Value's type.'''
        validated_value =  self._validate_type_tree(value, self.val_type,
                                                    self.len_max, self.len_min)

        if self.fun and not self.fun(validated_value):
            msg1 = 'Setting {} (value: {!r}, type: {}) is not '.format(self.name or validated_value,
                                                                       validated_value,
                                                                       type(validated_value).__name__)
            msg2 = 'valid according to the user function {}.'.format(self.fun.__name__)
            raise ValueError(msg1 + msg2)

        return validated_value


def _clean_type_name(val_type: ValType) -> str:
    '''Returns the clean name of the val_type'''
    if val_type.__module__ == 'typing':
        type_name = str(val_type).replace('typing.', '')
    else:
        type_name = val_type.__name__
    return type_name.replace('__main__.', '')


class NamedValue(Value):
    '''Similar to Value, but it has a key (which must be hashable) and
        it validates a dictionary that contains the key and a value with the type val_type.'''
    def __init__(self, key: Hashable, val_type: Union[ValType, Value], **kwargs: Any) -> None:
        '''The key must be hashable (often it's a string), val_type can be a Value instance
            (in this case the rest of the arguments are ignored),
            or a type, the rest of the arguments are as for Value.'''
        if isinstance(val_type, Value):
            # use the Value's parameters for this NamedValue
            value = val_type
            val_type = value.val_type
            kwargs = vars(value)
            del kwargs['val_type']
            del kwargs['name']
        super(NamedValue, self).__init__(val_type, name=str(key), **kwargs)
        self.key = key

    @log_exceptions_warnings
    def validate(self, value: T) -> Any:
        '''Checks that the value is a dictionary where the key is equal to the name
            and the value has type val_type.'''
        if not isinstance(value, Dict):
            msg = 'The value to validate ({}) is not a dictionary!'.format(value)
            raise ValueError(msg)
        if self.key not in value:
            msg = "Setting '{}' not in dictionary {}".format(self.name, value)
            raise ValueError(msg)
        parsed_key = self.key
        parsed_value = self._validate_type_tree(value[self.key], self.val_type,
                                                self.len_max, self.len_min)

        return {parsed_key: parsed_value}


class DictValue():
    '''Represents a dictionary of Values, each with a name and type.'''
    mandatory = Kind.mandatory
    optional = Kind.optional
    exclusive = Kind.exclusive

    @log_exceptions_warnings
    def __init__(self, values: Dict[Hashable, Union[Value, ValType]],
                 kind: Kind = Kind.mandatory) -> None:
        '''values is a dictionary with the keys hashable
            and the values are simple types, Value instances or dictionaries of either.'''
        if isinstance(values, Dict):
            self.values_list = [NamedValue(key, value if not isinstance(value, Dict)
                                                else DictValue(value))
                                for key, value in values.items()]
        else:
            msg = 'The first argument must be a dictionary.'
            raise ValueError(msg)
        self.kind = kind

        value_names = ', '.join('{}: {}'.format(repr(value.key), _clean_type_name(value.val_type))
                      for value in self.values_list)
        self.__name__ =  '{}({})'.format(self.__class__.__name__, value_names)


    def __repr__(self) -> str:
        return self.__name__

    def __call__(self, config_dict: Dict) -> Dict:
        '''Pretend to be a type so typing module doesn't complain'''
        return self.validate(config_dict)

    @log_exceptions_warnings
    def _check_extra_and_exclusive(self, config_dict: Dict) -> None:
        '''Check that exclusive values are not present at the same time.
            Warn if extra values are present.'''
        present_values = set(config_dict.keys())

        needed_values = set(val.name for val in self.values_list if val.kind is Kind.mandatory)
        optional_values = set(val.name for val in self.values_list if val.kind is Kind.optional)
        exclusive_values = set(val.name for val in self.values_list if val.kind is Kind.exclusive)
        optional_values = optional_values | exclusive_values

        set_extra = present_values - needed_values
        # if there are extra values and they aren't optional
        if set_extra and not set_extra.issubset(optional_values):
            set_not_optional = set_extra - optional_values
            warnings.warn('Some values or sections should not be present in the file: ' +
                          str(set_not_optional), ConfigWarning)
        # exclusive values
        if len(exclusive_values) > 1 and exclusive_values.issubset(present_values):
            raise ValueError('Only one of the values in ' +
                             '{} can be present at the same time.'.format(exclusive_values))

    @log_exceptions_warnings
    def validate(self, config_dict: Dict) -> Dict:
        '''Return the validated dictionary'''
        if not isinstance(config_dict, Dict):
            msg = 'DictValues can only validate dictionaries!'
            raise ValueError(msg)

        self._check_extra_and_exclusive(config_dict)

        #  we are given a dictionary to match
        # store validated values
        parsed_dict = {}  # type: Dict
        for val in self.values_list:
            # skip optional values that aren't present
            if val.kind is not Value.mandatory and val.key not in config_dict:
                continue
            parsed_dict.update(val.validate(config_dict))
        return parsed_dict
