#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

"""
tabutils.typetools
~~~~~~~~~~~~~~~~~~

Provides methods for type guessing

Examples:
    basic usage::

        from tabutils.typetools import underscorify

        header = ['ALL CAPS', 'Illegal $%^', 'Lots of space']
        underscored = list(underscorify(header))

Attributes:
    NULL_YEAR (int): Year to be consider null
    NULL_TIME (str): ISO format time to be consider null
"""

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

from functools import partial
from datetime import datetime as dt, date, time

from . import fntools as ft, convert as cv

NULL_YEAR = 9999
NULL_TIME = '00:00:00'


def type_test(test, _type, key, value):
    try:
        passed = test(value)
    except AttributeError:
        replacements = [('type', ''), ('datetime.', '')]
        real_type = ft.mreplace(str(type(value)), replacements).strip(" '<>")
        result = {'id': key, 'type': real_type}
    else:
        result = {'id': key, 'type': _type} if passed else None

    return result


def guess_type_by_field(content):
    """Tries to determine field types based on field names.

    Args:
        content (Iter[str]): Field names.

    Yields:
        dict: Field type. The parsed field and its type.

    Examples:
        >>> fields = ['date', 'raw_value', 'date_and_time', 'length', 'field']
        >>> {r['id']: r['type'] for r in guess_type_by_field(fields)} == {
        ...     u'date': u'date',
        ...     u'raw_value': u'float',
        ...     u'date_and_time': u'datetime',
        ...     u'length': u'float',
        ...     u'field': u'text',
        ... }
        ...
        True
    """
    floats = ('value', 'length', 'width', 'days')
    float_func = lambda x: ft.find(floats, [x], method='fuzzy')
    datetime_func = lambda x: ('date' in x) and ('time' in x)

    guess_funcs = [
        {'type': 'datetime', 'func': datetime_func},
        {'type': 'date', 'func': lambda x: 'date' in x},
        {'type': 'time', 'func': lambda x: 'time' in x},
        {'type': 'float', 'func': float_func},
        {'type': 'int', 'func': lambda x: 'count' in x},
        {'type': 'text', 'func': lambda x: True},
    ]

    for item in content:
        for g in guess_funcs:
            result = type_test(g['func'], g['type'], item, item)

            if result:
                yield result
                break


def guess_type_by_value(record, blanks_as_nulls=True, strip_zeros=False):
    """Tries to determine field types based on values.

    Args:
        record (dict): The row to guess.
        blanks_as_nulls (bool): Treat empty strings as null (default: True).
        strip_zero (bool):

    Yields:
        dict: Field type. The parsed field and its type.

    Examples:
        >>> record = {
        ...     'null': 'None',
        ...     'bool': 'false',
        ...     'int': '1',
        ...     'float': '1.5',
        ...     'text': 'Iñtërnâtiônàližætiøn',
        ...     'date': '5/4/82',
        ...     'time': '2:30',
        ...     'datetime': '5/4/82 2pm',
        ... }
        >>> {r['id']: r['type'] for r in guess_type_by_value(record)} == {
        ...     u'null': u'null',
        ...     u'bool': u'bool',
        ...     u'int': u'int',
        ...     u'float': u'float',
        ...     u'text': u'text',
        ...     u'date': u'date',
        ...     u'time': u'time',
        ...     u'datetime': u'datetime'}
        ...
        True
        >>> record = {
        ...     'null': None,
        ...     'bool': False,
        ...     'int': 10,
        ...     'float': 1.5,
        ...     'text': 'Iñtërnâtiônàližætiøn',
        ...     'date': date(1982, 5, 4),
        ...     'time': time(2, 30),
        ...     'datetime': dt(1982, 5, 4, 2),
        ... }
        >>> {r['id']: r['type'] for r in guess_type_by_value(record)} == {
        ...     u'null': u'null',
        ...     u'bool': u'bool',
        ...     u'int': u'int',
        ...     u'float': u'float',
        ...     u'text': u'text',
        ...     u'date': u'date',
        ...     u'time': u'time',
        ...     u'datetime': u'datetime'}
        ...
        True
    """
    null_func = partial(ft.is_null, blanks_as_nulls=blanks_as_nulls)
    int_func = partial(ft.is_int, strip_zeros=strip_zeros)
    float_func = partial(ft.is_numeric, strip_zeros=strip_zeros)

    guess_funcs = [
        {'type': 'null', 'func': null_func},
        {'type': 'bool', 'func': ft.is_bool},
        {'type': 'int', 'func': int_func},
        {'type': 'float', 'func': float_func},
        {'type': 'datetime', 'func': is_datetime},
        {'type': 'time', 'func': is_time},
        {'type': 'date', 'func': is_date},
        {'type': 'text', 'func': lambda x: hasattr(x, 'lower')}]

    for key, value in record.iteritems():
        for g in guess_funcs:
            result = type_test(g['func'], g['type'], key, value)

            if result:
                yield result
                break
        else:
            raise TypeError("Couldn't guess type of '%s'" % value)


def is_date(content):
    """ Determines whether or not content can be converted into a date

    Args:
        content (scalar): the content to analyze

    Examples:
        >>> is_date('5/4/82 2pm')
        True
        >>> is_date('5/4/82')
        True
        >>> is_date('2pm')
        False
        >>> is_date(dt(1982, 5, 4, 2))
        True
        >>> is_date(date(1982, 5, 4))
        True
        >>> is_date(time(2, 30))
        False
    """
    try:
        converted = cv.to_datetime(content)
    except TypeError:
        converted = content

    try:
        the_year = converted.date().year
    except AttributeError:
        if hasattr(converted, 'timetuple'):
            the_year = converted.year  # it's a date
        else:
            the_year = NULL_YEAR  # it's a time

    return converted and the_year != NULL_YEAR


def is_time(content):
    """ Determines whether or not content can be converted into a time

    Args:
        content (scalar): the content to analyze

    Examples:
        >>> is_time('5/4/82 2pm')
        True
        >>> is_time('5/4/82')
        False
        >>> is_time('2pm')
        True
        >>> is_time(dt(1982, 5, 4, 2))
        True
        >>> is_time(date(1982, 5, 4))
        False
        >>> is_time(time(2, 30))
        True
    """
    try:
        converted = cv.to_datetime(content)
    except TypeError:
        converted = content

    try:
        the_time = converted.time().isoformat()
    except AttributeError:
        if hasattr(converted, 'timetuple'):
            the_time = NULL_TIME  # it's a date
        else:
            the_time = converted.isoformat()  # it's a time

    return converted and the_time != NULL_TIME


def is_datetime(content):
    """ Determines whether or not content can be converted into a datetime

    Args:
        content (scalar): the content to analyze

    Examples:
        >>> is_datetime('5/4/82 2pm')
        True
        >>> is_datetime('5/4/82')
        False
        >>> is_datetime('2pm')
        False
        >>> is_datetime(dt(1982, 5, 4, 2))
        True
        >>> is_datetime(date(1982, 5, 4))
        False
        >>> is_datetime(time(2, 30))
        False
    """
    try:
        converted = cv.to_datetime(content)
    except TypeError:
        converted = content

    try:
        the_year = converted.date().year
    except AttributeError:
        the_year = NULL_YEAR

    try:
        the_time = converted.time().isoformat()
    except AttributeError:
        the_time = NULL_TIME

    has_date = converted and the_year != NULL_YEAR
    has_time = converted and the_time != NULL_TIME
    return has_date and has_time