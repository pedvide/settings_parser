# -*- coding: utf-8 -*-
"""
Created on Sun Apr  2 17:03:04 2017

@author: Villanueva
"""

import warnings
import pytest

from settings_parser.util import log_exceptions_warnings


def test_log_exceptions_warnings_nothing():
    '''Tests the logging of exceptions and warnings'''

    # no exceptions or warnings
    @log_exceptions_warnings
    def raise_nothing(arg1, arg2=1):
        return str(arg1) + str(arg2)
    raise_nothing('a', arg2=6)

def test_log_exceptions_warnings_warning(caplog):
    '''Tests the logging of exceptions and warnings'''

    # warning
    @log_exceptions_warnings
    def raise_warning(arg1, arg2=1):
        warnings.warn(str(arg1) + str(arg2))
    raise_warning('asd', arg2=6)
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert 'UserWarning: "asd6" in test_util.py' in caplog.text

def test_log_exceptions_warnings_exception(caplog):
    '''Tests the logging of exceptions and warnings'''

    # exception
    @log_exceptions_warnings
    def raise_exception(arg1, arg2=1):
        return 1/0
    with pytest.raises(ZeroDivisionError) as excinfo:
        raise_exception('a', arg2=6)
    assert excinfo.type == ZeroDivisionError
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'ERROR'
    assert 'division by zero' in caplog.text
