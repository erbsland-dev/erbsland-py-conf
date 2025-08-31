#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime as dt
import re

import pytest

from erbsland.conf.datetime import DateTime, Time
from erbsland.conf.time_delta import TimeDelta
from erbsland.conf.value_type import ValueType
from erbsland.conf.impl.value_storage_type import value_type_from_storage_type


@pytest.mark.parametrize(
    "storage_type, expected",
    [
        (str, ValueType.TEXT),
        (int, ValueType.INTEGER),
        (float, ValueType.FLOAT),
        (bool, ValueType.BOOLEAN),
        (dt.date, ValueType.DATE),
        (Time, ValueType.TIME),
        (dt.time, ValueType.TIME),
        (DateTime, ValueType.DATE_TIME),
        (dt.datetime, ValueType.DATE_TIME),
        (TimeDelta, ValueType.TIME_DELTA),
        (re.Pattern, ValueType.REGEX),
        (bytes, ValueType.BYTES),
    ],
)
def test_value_type_from_storage_type_known(storage_type, expected):
    assert value_type_from_storage_type(storage_type) == expected


def test_value_type_from_storage_type_unknown():
    with pytest.raises(ValueError):
        value_type_from_storage_type(list)
