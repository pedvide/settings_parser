# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 22:18:28 2017

@author: Villanueva
"""
from fractions import Fraction
import pytest
from settings_parser.value import Value, NamedValue

def idfn(value):
    '''Returns the name of the test according to the parameters'''
    return str(type(value).__name__) + '_' + str(value)

@pytest.mark.parametrize('value', [5, 1.25, 1+5j, Fraction(2,5),
                                   'a', 'asd', '\u00B5',
                                   True, b'2458', (4,5,6)], ids=idfn)
def test_NamedValue(value):
    '''Test the parsing of dictionary elements with NamedValue'''
    d = {value: 5}
    assert NamedValue(value, int).validate(d) == d  # simple constructor
    assert NamedValue(value, Value(int, val_max=6)).validate(d) == d  # constructor from Value
    d2 = {value: value}
    assert NamedValue(value, type(value)).validate(d2) == d2
    assert NamedValue(value, Value(type(value))).validate(d2) == d2

    # the key must match exactly
    with pytest.raises(ValueError) as excinfo:
        NamedValue(value, int).validate({'wrong_key': 5})
    assert excinfo.match(r"Setting ")
    assert excinfo.match(r" not in dictionary")
    assert excinfo.type == ValueError

    # the value must have the right type
    with pytest.raises(ValueError) as excinfo:
        NamedValue(value, int).validate({value: 'wrong_value'})
    assert excinfo.match('does not have the right type')
    assert excinfo.type == ValueError

    # the value to validate must be a dictionary
    with pytest.raises(ValueError) as excinfo:
        NamedValue(value, int).validate(value)
    assert excinfo.match('is not a dictionary')
    assert excinfo.type == ValueError