# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 00:45:53 2017

@author: Villanueva
"""

import pytest
#import numpy as np
from fractions import Fraction

from settings_parser.value import Value
from settings_parser.util import ValueTypeError
from typing import Dict, List, Tuple, Set, Union, Callable


def idfn(value):
    '''Returns the name of the test according to the parameters'''
    return str(type(value).__name__) + '_' + str(value)


#### SIMPLE TYPES


@pytest.mark.parametrize('value', [5, 1.25, 1+5j, Fraction(2,5),
                                   'a', 'asd', '\u00B5', {'a': 2},
                                   True, b'2458', [1,2,3], (4,5,6), {7,8,9}], ids=idfn)
def test_always_right_casts(value):
    '''Parsing a value of the same type as expected should aways work
        and return the same value.'''
    assert Value(type(value)).validate(value) == value
    assert type(Value(type(value)).validate(value)) == type(value)


def test_wrong_casts():
    '''validate values that cannot be converted to the requested type.'''
    with pytest.raises(ValueError) as excinfo:
        Value(int).validate('50.0')
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(int).validate(5+0j)
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(bytes).validate('asd')
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError


def test_wrong_generics():
    '''Test that using a generic without arguments fails'''
    with pytest.raises(ValueError) as excinfo:
        Value(List).validate([1,2,3])
    assert excinfo.match("Invalid requested type \(List\), generic types must contain arguments.")
    assert excinfo.type == ValueError


def test_str_to_num():
    '''Test conversion from str to numbers.'''

    assert Value(int).validate('25') == 25
    assert Value(float).validate('25.0') == 25.0
    assert Value(complex).validate('2+5j') == 2+5j
    assert Value(Fraction).validate('79/98') == Fraction(79,98)


def test_num_to_str():
    '''Test conversion from numbers to strings.'''

    assert Value(str).validate(25) == '25'
    assert Value(str).validate(25.0) == '25.0'
    assert Value(str).validate(2+5j) == '(2+5j)'
    assert Value(str).validate(Fraction(78/98)) == '3584497662601007/4503599627370496'


def test_num_to_num():
    '''Test converions between numbers of different types.'''

    # int, Fraction to float
    assert Value(float).validate(25) == 25.0
    assert Value(float).validate(Fraction(89,5)) == 17.8
    # float, Fraction to int
    assert Value(int).validate(12.2) == 12
    assert Value(int).validate(Fraction(10,5)) == 2
    # int, float to Fraction
    assert Value(Fraction).validate(7) == Fraction(7,1)
    assert Value(Fraction).validate(56.2) == Fraction(3954723422784717, 70368744177664)
    # int, float, Fraction to complex
    assert Value(complex).validate(25) == 25+0j
    assert Value(complex).validate(12.2) == 12.2+0j
    assert Value(complex).validate(Fraction(10,5)) == 2+0j


def test_max_min_val():
    '''Test that max and min values work'''

    assert Value(int, val_max=30, val_min=5).validate(25) == 25
    assert Value(int, val_max=30, val_min=5).validate(30) == 30
    assert Value(int, val_max=30, val_min=5).validate(5) == 5

    with pytest.raises(ValueError) as excinfo:
        Value(int, val_max=30, val_min=5).validate(50)
    assert excinfo.match("cannot be larger than")
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(int, val_max=30, val_min=5).validate(-5)
    assert excinfo.match("cannot be smaller than")
    assert excinfo.type == ValueError

    # val_max/min can only be used with types that have __gt__/__lt__ methods
    with pytest.raises(ValueTypeError) as excinfo:
        Value(str, val_max=30, val_min=5).validate(5)
    assert excinfo.match("Value 5 of type str cannot be compared to")
    assert excinfo.type == ValueTypeError


def test_str_len():
    '''Test the max and min length of a simple str.'''
    assert Value(str, len_max=3).validate('abc')
    with pytest.raises(ValueError) as excinfo:
        Value(str, len_max=3).validate('abcd')
    assert excinfo.match('cannot be larger than 3.')
    assert excinfo.type == ValueError

    assert Value(str, len_max=3).validate(123)
    with pytest.raises(ValueError) as excinfo:
        Value(str, len_max=3).validate(1234)
    assert excinfo.match('cannot be larger than 3.')
    assert excinfo.type == ValueError


def test_simple_unions():
    '''Test that Unions of simple types go through each member.'''
    assert Value(Union[int, str]).validate(12.0) == 12
    assert Value(Union[int, str]).validate('12.0') == '12.0'

    assert Value(Union[float, complex]).validate(5+0j) == 5+0j
    assert Value(Union[float, Fraction]).validate('5/2') == Fraction(5,2)

    with pytest.raises(ValueError) as excinfo:
        Value(Union[int, float]).validate(5+1j)
    assert excinfo.match("does not have any of the right types")
    assert excinfo.type == ValueError


def test_nested_unions():
    '''Test Unions of Sequences and simple types'''
    assert Value(Union[int, List[int]]).validate(12) == 12
    assert Value(Union[int, List[int]]).validate([12]) == [12]
    assert Value(Union[int, List[int]]).validate([12, 13, 14]) == [12, 13, 14]

    assert Value(Union[List[int],
                              List[List[int]]]).validate([[1,2,3],
                                                       [4,5,6]]) ==  [[1, 2, 3], [4, 5, 6]]

    with pytest.raises(ValueError) as excinfo:
        Value(Union[int, List[int]]).validate(5+1j)
    assert excinfo.match("does not have any of the right types")
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(Union[int, List[int]], len_max=2).validate([12, 13, 14])
    assert excinfo.match("does not have any of the right types")
    assert excinfo.type == ValueError


def test_own_types():
    '''Test that user-defined types, such as combination of other types, work.'''
    class f_float:
        '''Simulates a type that converts numbers or str into floats through Fraction.'''
        def __new__(cls, x: str) -> float:
            '''Return the float'''
            return float(Fraction(x))  # type: ignore
    f_float.__name__ = 'float(Fraction())'

    # good
    assert Value(f_float).validate('4/5') == 0.8

    # wrong
    with pytest.raises(ValueError) as excinfo:
        Value(f_float).validate('asd')
    assert excinfo.match(r"does not have the right type \(float\(Fraction\(\)\)\).")
    assert excinfo.type == ValueError


def test_unknown_type():
    '''Test that invalid types are recognized as such.'''
    with pytest.raises(TypeError) as excinfo:
        Value(Callable).validate(5)
    assert excinfo.match(r"Type not recognized or supported")
    assert excinfo.type == TypeError


def test_custom_functions():
    '''Test user-defined functions that restrict the value.'''
    assert Value(int, fun=lambda x: x!=5).validate(4) == 4
    assert Value(int, fun=lambda x: x!=5).validate(6) == 6

    with pytest.raises(ValueError) as excinfo:
        Value(int, fun=lambda x: x!=5).validate(5)
    assert excinfo.match(r"is not valid according to the user function")
    assert excinfo.type == ValueError

    assert Value(List[int], fun=lambda lst: all(x==6 for x in lst)).validate([6, 6, 6]) == [6, 6, 6]


def test_argument_expansion():
    '''Test types with more than one argument in the constructor.'''
    import datetime

    with pytest.raises(ValueError) as excinfo:
        Value(datetime.date).validate([2015, 5, 3])
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError

    assert Value(datetime.date, expand_args=True).validate((2015, 5, 3)) == datetime.date(2015, 5, 3)
    assert Value(datetime.date, expand_args=True).validate({'year': 2015, 'month': 5, 'day': 3}) == datetime.date(2015, 5, 3)

    with pytest.raises(ValueError) as excinfo:
        Value(datetime.date, expand_args=True).validate(2015)
    assert excinfo.match('Expected a list or a dictionary')
    assert excinfo.type == ValueError
#### LISTS AND SEQUENCES

def test_simple_lists():
    '''Test lists of simple types.'''
    assert Value(List[int]).validate([1, 2]) == [1, 2]
    assert Value(List[float]).validate([1, 2.5, -9.1]) == [1, 2.5, -9.1]
    assert Value(List[str]).validate([1, 'a', 'asd', '\u2569']) == ['1', 'a', 'asd', '╩']
    assert Value(List[Union[int, str]]).validate([5, '6.0', 'a']) == [5, '6.0', 'a']

    with pytest.raises(ValueError) as excinfo:
        Value(List[int]).validate('56')
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError


def test_simple_list_len():
    '''Test the max and min length of a simple list.'''
    assert Value(List[int], len_max=4, len_min=2).validate([1, 2, 3]) == [1, 2, 3]
    assert Value(List[int], len_max=4, len_min=1).validate([1,2]) == [1, 2]
    assert Value(List[int], len_max=4, len_min=2).validate([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert Value(List[int], len_max=3, len_min=3).validate([1, 2, 3]) == [1, 2, 3]
    assert Value(List[int], len_min=3).validate([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert Value(List[int], len_max=3).validate([1, 2]) == [1, 2]

    with pytest.raises(ValueError) as excinfo:
        Value(List[int], len_max=4, len_min=2).validate([1])
    assert excinfo.match('cannot be smaller than')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(List[int], len_max=4, len_min=2).validate([1, 2, 3, 4, 5])
    assert excinfo.match('cannot be larger than')
    assert excinfo.type == ValueError


def test_list_len_val():
    '''Test both the list's length and the size of the values'''
    assert Value(List[int], val_max=5, val_min=1,
                 len_max=4, len_min=1).validate([1,2]) == [1, 2]
    assert Value(List[int], val_max=5, val_min=1,
                 len_max=4, len_min=1).validate([4]) == [4]
    assert Value(List[int], val_max=5, val_min=1,
                 len_max=4, len_min=1).validate([1,2]) == [1, 2]

def test_tuples():
    '''Tuples can have any number of sub-types, which must match exactly.'''
    assert Value(Tuple[int]).validate([1, ]) == (1,)
    assert Value(Tuple[int, int]).validate([1, 2]) == (1, 2)
    assert Value(Tuple[int, str]).validate((1, 'asd')) == (1, 'asd')

    with pytest.raises(ValueError) as excinfo:
        Value(Tuple[int]).validate([1, 2])
    assert excinfo.match('Details: "Tuples must have the same number of sub-types and values."')
    assert excinfo.type == ValueError

def test_simple_sequences():
    '''Test sets'''
    assert Value(Set[float]).validate([1, 2.5, -9.1, 1]) == {1, 2.5, -9.1}
#    assert Value(Deque[str]).validate('hjkl') == deque(['h', 'j', 'k', 'l'])


def test_nested_lists():
    '''Test lists of lists of simple types'''
    assert Value(List[List[int]]).validate([[1, 2, 3], [4, 5, 6]]) == [[1, 2, 3], [4, 5, 6]]
    assert Value(List[List[str]]).validate([['asd', 'dsa'],
                                                ['t', 'y', 'i']]) == [['asd', 'dsa'],
                                                                      ['t', 'y', 'i']]
    assert Value(List[Set[Tuple[int, float]]]).validate([[[1,2],[1,2]],
                                                     [[4,5], [6,7]]]) == [{(1, 2.0)}, {(4, 5.0),
                                                                                     (6, 7.0)}]

    # this is a list of lists of str, and works
    assert Value(List[List[str]]).validate([['a'], ['s'], ['d'],
                                                ['d'], ['s'], ['a']]) == [['a'], ['s'], ['d'],
                                                                          ['d'], ['s'], ['a']]
    assert Value(List[List[List[str]]]).validate([[[1], [2]],
                                                      [[4], [5]]]) == [[['1'], ['2']],
                                                                       [['4'], ['5']]]


    with pytest.raises(ValueError) as excinfo:
        # this is a list of str, not lists of list of str (even though str is iterable)!!
        Value(List[List[str]]).validate(['asddsa'])
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError


def test_nested_lists_len():
    '''Test the length of nested lists'''
    assert Value(List[List[int]]).validate([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]

    assert Value(List[List[int]],
                 len_max=[2,2]).validate([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]
    assert Value(List[List[int]],
                 len_min=[2,3]).validate([[1, 2, 3], [4, 5, 6]]) == [[1, 2, 3], [4, 5, 6]]
    assert Value(List[List[int]],
                 len_max=[None,2]).validate([[1, 2], [4, 5], [4, 5]]) == [[1, 2], [4, 5], [4, 5]]


    with pytest.raises(ValueError) as excinfo:
        Value(List[List[int]], len_max=[2,2]).validate([[1, 2], [4, 5], [7, 8]])
    assert excinfo.match('cannot be larger than')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(List[List[int]], len_min=[2,4]).validate([[1, 2, 3], [4, 5, 6, 7]])
    assert excinfo.match('cannot be smaller than')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(List[List[int]], len_max=[None,2]).validate([[1, 2], [4, 5], [4, 5, 5]])
    assert excinfo.match('cannot be larger than')
    assert excinfo.type == ValueError


#### DICTIONARIES

def test_simple_dicts():
    '''Test the parsing of simple dictionaries.'''
    d = {'a': '1'}
    assert Value(Dict[str, str]).validate(d) == d
    assert Value(Dict[str, int]).validate(d) == {'a': 1}
    assert Value(Dict[str, float]).validate(d) == {'a': 1.0}
    assert Value(Dict[str, complex]).validate(d) == {'a': (1+0j)}

    d4 = {'a': 1, 'b': '3', 'c': 56.2}
    assert Value(Dict[str, int]).validate(d4) == {'a': 1, 'b': 3, 'c': 56}
    assert Value(Dict[str, str]).validate(d4) == {'a': '1', 'b': '3', 'c': '56.2'}

    d2 = {1: 5}
    assert Value(Dict[str, str]).validate(d2) == {'1': '5'}
    assert Value(Dict[str, int]).validate(d2) == {'1': 5}
    assert Value(Dict[int, str]).validate(d2) == {1: '5'}
    assert Value(Dict[int, int]).validate(d2) == {1: 5}

    assert Value(Dict[str, Union[int, str]]).validate({'a': 1}) == {'a': 1}
    assert Value(Dict[str, Union[int, str]]).validate({'a': '1'}) == {'a': 1}
    assert Value(Dict[str, Union[int, str]]).validate({'a': 'b'}) == {'a': 'b'}

    assert Value(Dict[str, List[int]]).validate({'a': [1, 2, 3]}) == {'a': [1, 2, 3]}
    assert Value(Dict[str, List[int]],
                 len_max=[1,3]).validate({'a': [1, 2, 3]}) == {'a': [1, 2, 3]}

    assert Value(Dict[str, Set[int]],
                 len_max=[1,3]).validate({'a': [1, 2, 2]}) == {'a': {1, 2}}

    d3 = {(1,2): [3, 4]}
    assert Value(Dict[Tuple[int, int], List[int]]).validate(d3) == d3
    # this works too
    assert Value(Dict[tuple, List[int]]).validate(d3) == d3

    with pytest.raises(ValueError) as excinfo:
        Value(Dict[int, int]).validate(d)
    assert excinfo.match("Setting")
    assert excinfo.match("\(value: 'a', type: str\)")
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(Dict[str, Union[int, complex]]).validate({'a': 'b'})
    assert excinfo.match("Setting")
    assert excinfo.match("\(value: 'b', type: str\)")
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(Dict[str, int]).validate(None)
    assert excinfo.match("Setting")
    assert excinfo.match("\(value: None, type: NoneType\)")
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError

    with pytest.raises(ValueError) as excinfo:
        Value(Dict[str, int]).validate(5)
    assert excinfo.match("Setting")
    assert excinfo.match('does not have the right type')
    assert excinfo.match("This type can only validate dictionaries")
    assert excinfo.type == ValueError


def test_nested_dicts():
    '''Test the parsing of nested dictionaries.'''
    d = {'a': {('b', 2): 4}}
    assert Value(Dict[str, Dict[Tuple[str, int], int]]).validate(d) == {'a': {('b', 2): 4}}
    assert Value(Dict[str, Dict[Tuple[str, int], str]]).validate(d) == {'a': {('b', 2): '4'}}

def test_dict_with_Value():
    d4 = {'a': 1, 'b': '3', 'c': 56.2}
    assert Value(Dict[str, Value(int)]).validate(d4) == {'a': 1, 'b': 3, 'c': 56}

