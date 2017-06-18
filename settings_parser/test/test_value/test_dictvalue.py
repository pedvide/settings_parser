# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 22:20:19 2017

@author: Villanueva
"""
from typing import Dict, List
import pytest
from settings_parser.value import Value, DictValue
from settings_parser.util import ConfigWarning


def test_DictValue():
    '''Test DictValues'''
    d = {'age': 28, 'city': 'utrecht'}
    # simple type list
    dval1 = DictValue({'age': int, 'city': str})
    assert dval1.validate(d) == d
    # Value list
    dval2 = DictValue({'age': Value(int, val_min=0), 'city': Value(str)})
    assert dval2.validate(d) == d
    # mixed
    dval3 = DictValue({'age': Value(int, val_min=0), 'city': str})
    assert dval3.validate(d) == d
    # both methods create the same DictValues, their reprs are equal
    assert repr(dval1) == repr(dval2)
    assert repr(dval1) == repr(dval3)

    d = {'age': 28}
    # list of names and types is not a valid constructor
    with pytest.raises(ValueError) as excinfo:
        DictValue(['age', str]).validate(d)
    assert excinfo.match("The first argument must be a dictionary")
    assert excinfo.type == ValueError

    d = 'not a dictionary'
    # DictValues only validate dictionaries
    with pytest.raises(ValueError) as excinfo:
        DictValue({'age': int}).validate(d)
    assert excinfo.match("DictValues can only validate dictionaries")
    assert excinfo.type == ValueError

    # extra key:value pairs are ok, but they give off a warning and are ignored
    d = {'age': 28, 'city': 'utrecht'}
    d2 = {'age': 28, 'city': 'utrecht', 'extra': True}
    with pytest.warns(ConfigWarning) as warnings:
        assert DictValue({'age': int, 'city': str}).validate(d2) == d
    assert len(warnings) == 1 # one warning
    warning = warnings.pop(ConfigWarning)
    assert warning.category == ConfigWarning
    assert 'Some values or sections should not be present in the file' in str(warning.message)

    d = {'age': 28}
    # the dict doesn't contain all keys
    with pytest.raises(ValueError) as excinfo:
        DictValue({'age': int, 'city': str}).validate(d)
    assert excinfo.match("Setting ")
    assert excinfo.match("not in dictionary")
    assert excinfo.type == ValueError

    d = {'ag': 28, 'city': 'utrecht'}
    # wrong key name
    with pytest.raises(ValueError) as excinfo:
        DictValue({'age': int, 'city': str}).validate(d)
    assert excinfo.match("Setting ")
    assert excinfo.match("not in dictionary")
    assert excinfo.type == ValueError

    d = {'age': 'asd', 'city': 'utrecht'}
    # wrong value type
    with pytest.raises(ValueError) as excinfo:
        DictValue({'age': int, 'city': str}).validate(d)
    assert excinfo.match("Setting ")
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError

    # DictValue in Value
    d = {'age': 28, 'city': 'utrecht'}
    assert Value(DictValue({'age': int, 'city': str})).validate(d) == d


def test_optional():
    '''Test that optional values are validated if present, but no error is raised if not.'''
    d1 = {'age': 28, 'city': 'utrecht'}
    d2 = {'city': 'utrecht'}
    dval = DictValue({'age': Value(int, kind=Value.optional), 'city': str})
    assert dval.validate(d1) == d1
    assert dval.validate(d2) == d2


def test_exclusive():
    '''Test exclusive values.'''
    d1 = {'age': 28}
    dval = DictValue({'age': Value(int, kind=Value.exclusive)})
    assert dval.validate(d1) == d1
    dval2 = DictValue({'age': Value(int, kind=Value.exclusive),
                      'city': Value(str, kind=Value.exclusive)})
    # only one of them is present, ok
    assert dval2.validate(d1) == d1

    d2 = {'age': 28, 'city': 'utrecht'}
    with pytest.raises(ValueError) as excinfo:
        dval2.validate(d2)
    assert excinfo.match("Only one of the values")
    assert excinfo.match("can be present at the same time")
    assert excinfo.type == ValueError


def test_nested_DictValue():
    '''Test DictValues with other DictValues as types.'''
    d = {'subsection1': {'subsubsection1': 'asd', 'subsubsection2': 5}, 'subsection2': [1,2,3]}
    assert DictValue({'subsection1': DictValue({'subsubsection1': str, 'subsubsection2': int}),
                      'subsection2': Value(List[int])}).validate(d) == d
    # avoid repetition of DictValue in nested types
    assert DictValue({'subsection1': {'subsubsection1': str, 'subsubsection2': int},
                      'subsection2': Value(List[int])}).validate(d) == d

    d2 = {'subsection1': {'subsubsection1': 'asd', 'subsubsection2': 5}, 'subsection2': 1}
    with pytest.raises(ValueError) as excinfo:
        DictValue({'subsection1': {'subsubsection1': str, 'subsubsection2': int},
                   'subsection2': Value(List[int])}).validate(d2)
    assert excinfo.match("Setting subsection2")
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError


def test_DictValue_in_Dict():
    '''Test the combination of DictValue and Dict.'''
    d = {'key1': {'age': 28, 'city': 'utrecht'},
         'key2' : {'age': 52, 'city': 'london'},
         'key3': {'age': 24, 'city': 'rome'}}
    assert Value(Dict[str, DictValue({'age': int, 'city': str})]).validate(d) == d

    # wrong key type
    with pytest.raises(ValueError) as excinfo:
        assert Value(Dict[int, DictValue({'age': int, 'city': str})]).validate(d) == d
    assert excinfo.match("Setting")
    assert excinfo.match("does not have the right type")
    assert excinfo.type == ValueError

    # wrong key type
    with pytest.raises(ValueError) as excinfo:
        assert Value(Dict[int, DictValue({'age': int, 'city': str})]).validate(45) == d
    assert excinfo.match("Setting")
    assert excinfo.match("does not have the right type")
    assert excinfo.match("This type can only validate dictionaries")
    assert excinfo.type == ValueError


