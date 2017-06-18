# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 16:48:45 2017

@author: villanueva
"""
from fractions import Fraction
import sys
import datetime
from typing import List, Tuple, Union, Dict
from settings_parser.value import Value, DictValue

class f_float(type):
    '''Type that converts numbers or str into floats through Fraction.'''
    def __new__(mcs, x: str) -> float:
        '''Return the float'''
        return float(Fraction(x))  # type: ignore
f_float.__name__ = 'float(Fraction())'

# smallest float number
min_float = sys.float_info.min

Vector = Tuple[f_float, f_float, f_float]
settings = {'version': Value(int, val_min=1, val_max=1),
            'section': DictValue({'subsection1': {'subsubsection1': str, 'subsubsection2': int},
                                  'subsection2': Value(List[int])}),
            'people': Value(Dict[str, DictValue({'age': int, 'city': str})]),  #  type: ignore
           }
