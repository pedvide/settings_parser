# -*- coding: utf-8 -*-
"""
Created on Wed Nov 23 16:45:32 2016

@author: Pedro
"""

import sys
import tempfile
from contextlib import contextmanager
import os
import logging
import warnings
from functools import wraps

from typing import Generator, Callable, Any, Tuple, Dict


# http://stackoverflow.com/a/11892712
@contextmanager
def temp_filename(data: str = None, mode: str = 'wt') -> Generator:
    '''Creates a temporary file and writes text data to it. It returns its filename.
        It deletes the file after use in a context manager.
    '''
    # file won't be deleted after closing
    temp = tempfile.NamedTemporaryFile(mode=mode, delete=False)
    if data:
        temp.write(data)
    temp.close()
    try:
        yield temp.name
    finally:
        os.unlink(temp.name)  # delete file


def log_exceptions_warnings(function: Callable) -> Callable:
    '''Decorator to log exceptions and warnings'''
    @wraps(function)
    def wrapper(*args: Tuple, **kwargs: Dict) -> Any:
        try:
            with warnings.catch_warnings(record=True) as warn_list:
                # capture all warnings
                warnings.simplefilter('always')
                ret = function(*args, **kwargs)
        except Exception as exc:
            logger = logging.getLogger(function.__module__)
            logger.error(exc.args[0])
            raise
        for warn in warn_list:
            logger = logging.getLogger(function.__module__)
            msg = (warn.category.__name__ + ': "' + str(warn.message) +
                   '" in ' + os.path.basename(warn.filename) +
                   ', line: ' + str(warn.lineno) + '.')
            logger.warning(msg)
            # re-raise warnings
            warnings.warn(msg, warn.category)
        return ret
    return wrapper


@contextmanager
def console_logger_level(level: int) -> Generator:  # pragma: no cover
    '''Temporary change the console handler level.'''
    logger = logging.getLogger()  # root logger
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            if handler.stream == sys.stdout:  # type: ignore
                old_level = handler.level
                handler.setLevel(level)
                yield None
                handler.setLevel(old_level)
                return
    # in case no console handler exists
    yield None
    return


@contextmanager
def no_logging() -> Generator:
    '''Temporary disable all logging.'''
    logging.disable(logging.CRITICAL)
    yield None
    logging.disable(logging.NOTSET)


class ValueTypeError(TypeError):
    '''The type passed to Value is not valid.'''
    pass


class ConfigError(SyntaxError):
    '''Something in the configuration file is not correct'''
    pass


class ConfigWarning(UserWarning):
    '''Something in the configuration file is not correct'''
    pass
