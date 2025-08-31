#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import re
from pathlib import Path

import pytest

from erbsland.conf.parser import load
from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.value_type import ValueType
from erbsland.conf.error import ConfTypeMismatch
from erbsland.conf.name import RegularName
from erbsland.conf.name_path import NamePath
from erbsland.conf.time_delta import TimeUnit, TimeDelta

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def doc_single_values():
    return load(DATA_DIR / "single_values.elcl")


class TestValueAs:

    @pytest.mark.parametrize(
        "method,name_path,expected",
        [
            pytest.param("as_int", "main.value_int", 12345, id="int"),
            pytest.param("as_bool", "main.value_bool", True, id="bool"),
            pytest.param("as_float", "main.value_float", 12.345, id="float"),
            pytest.param("as_text", "main.value_text", "This is Text", id="text"),
            pytest.param("as_date", "main.value_date", datetime.date(2026, 8, 10), id="date"),
            pytest.param(
                "as_time", "main.value_time", Time(17, 54, second=12, tzinfo=datetime.timezone.utc), id="time"
            ),
            pytest.param(
                "as_date_time",
                "main.value_date_time",
                DateTime(2026, 8, 10, hour=17, minute=54, second=12, tzinfo=datetime.timezone.utc),
                id="datetime",
            ),
            pytest.param("as_bytes", "main.value_bytes", b"\x01\x02\x03\xfd\xfe\xff", id="bytes"),
            pytest.param("as_time_delta", "main.value_time_delta", TimeDelta(10, TimeUnit.DAY), id="timedelta"),
            pytest.param("as_regex", "main.value_regex", re.compile("regex"), id="regex"),
            pytest.param("as_value_list", "main.value_list", [1, 2, 3], id="value_list"),
        ],
    )
    def test_as_named_type(self, doc_single_values, method, name_path, expected):
        value = doc_single_values[name_path]
        m = getattr(value, method)
        assert callable(m)
        # Use without default.
        actual_native_value = m()
        if value.type == ValueType.VALUE_LIST:
            assert isinstance(actual_native_value, list)
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Use with a default.
        actual_native_value = m(default=42)
        if value.type == ValueType.VALUE_LIST:
            assert isinstance(actual_native_value, list)
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Provoke an error by using the method on a section (that will never match the requested type).
        value = doc_single_values["main"]
        m = getattr(value, method)
        with pytest.raises(ConfTypeMismatch):
            actual_native_value = m()
        # Provoke using the default value.
        expect_default = m(default=42)
        assert expect_default == 42
        expect_default = m(default=None)
        assert expect_default is None

    @pytest.mark.parametrize(
        "requested_type,name_path,expected",
        [
            pytest.param(int, "main.value_int", 12345, id="int"),
            pytest.param(bool, "main.value_bool", True, id="bool"),
            pytest.param(float, "main.value_float", 12.345, id="float"),
            pytest.param(str, "main.value_text", "This is Text", id="text"),
            pytest.param(datetime.date, "main.value_date", datetime.date(2026, 8, 10), id="date"),
            pytest.param(Time, "main.value_time", Time(17, 54, second=12, tzinfo=datetime.timezone.utc), id="time"),
            pytest.param(
                DateTime,
                "main.value_date_time",
                DateTime(2026, 8, 10, hour=17, minute=54, second=12, tzinfo=datetime.timezone.utc),
                id="datetime",
            ),
            pytest.param(bytes, "main.value_bytes", b"\x01\x02\x03\xfd\xfe\xff", id="bytes"),
            pytest.param(TimeDelta, "main.value_time_delta", TimeDelta(10, TimeUnit.DAY), id="timedelta"),
            pytest.param(re.Pattern, "main.value_regex", re.compile("regex"), id="regex"),
            pytest.param(list, "main.value_list", [1, 2, 3], id="value_list"),
        ],
    )
    def test_as_type(self, doc_single_values, requested_type, name_path, expected):
        value = doc_single_values[name_path]
        # Use without default.
        actual_native_value = value.as_type(requested_type)
        if value.type == ValueType.VALUE_LIST:
            assert isinstance(actual_native_value, list)
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Use with a default.
        actual_native_value = value.as_type(requested_type, default=42)
        if value.type == ValueType.VALUE_LIST:
            assert isinstance(actual_native_value, list)
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Provoke an error by using the method on a section (that will never match the requested type).
        value = doc_single_values["main"]
        with pytest.raises(ConfTypeMismatch):
            actual_native_value = value.as_type(requested_type)
        # Provoke using the default value.
        expect_default = value.as_type(requested_type, default=42)
        assert expect_default == 42
        expect_default = value.as_type(requested_type, default=None)
        assert expect_default is None

    @pytest.mark.parametrize(
        "requested_type,value_name,expected",
        [
            pytest.param(int, "value_int", [1, 2, 3, 4, 5], id="int"),
            pytest.param(bool, "value_bool", [True, False, True], id="bool"),
            pytest.param(float, "value_float", [1.1, 2.2, 3.3], id="float"),
            pytest.param(str, "value_text", ["This is Text 1", "This is Text 2", "This is Text 3"], id="text"),
            pytest.param(
                datetime.date,
                "value_date",
                [
                    datetime.date(2026, 8, 10),
                    datetime.date(2026, 8, 11),
                    datetime.date(2026, 8, 12),
                ],
                id="date",
            ),
            pytest.param(
                Time,
                "value_time",
                [
                    Time(17, 54, second=12, tzinfo=datetime.timezone.utc),
                    Time(17, 54, second=13, tzinfo=datetime.timezone.utc),
                    Time(17, 54, second=14, tzinfo=datetime.timezone.utc),
                ],
                id="time",
            ),
            pytest.param(
                DateTime,
                "value_date_time",
                [
                    DateTime(2026, 8, 10, hour=17, minute=54, second=12, tzinfo=datetime.timezone.utc),
                    DateTime(2026, 8, 11, hour=17, minute=54, second=13, tzinfo=datetime.timezone.utc),
                    DateTime(2026, 8, 12, hour=17, minute=54, second=14, tzinfo=datetime.timezone.utc),
                ],
                id="datetime",
            ),
            pytest.param(
                bytes,
                "value_bytes",
                [
                    b"\x01\x02\x03",
                    b"\x04\x05\x06",
                    b"\x07\x08\x09",
                ],
                id="bytes",
            ),
            pytest.param(
                TimeDelta,
                "value_time_delta",
                [
                    TimeDelta(10, TimeUnit.DAY),
                    TimeDelta(20, TimeUnit.DAY),
                    TimeDelta(30, TimeUnit.DAY),
                ],
                id="timedelta",
            ),
            pytest.param(
                re.Pattern,
                "value_regex",
                [
                    re.compile("regex1"),
                    re.compile("regex2"),
                    re.compile("regex3"),
                ],
                id="regex",
            ),
        ],
    )
    def test_as_list(self, doc_single_values, requested_type, value_name, expected):
        name_path = NamePath([RegularName("value_lists"), RegularName(value_name)])
        value = doc_single_values[name_path]
        # No default value
        typed_list = value.as_list(requested_type)
        assert isinstance(typed_list, list)
        assert len(typed_list) == len(expected)
        for index, expected_value in enumerate(expected):
            assert typed_list[index] == expected_value
        # With default value
        typed_list = value.as_list(requested_type, default=[42])
        assert isinstance(typed_list, list)
        assert len(typed_list) == len(expected)
        for index, expected_value in enumerate(expected):
            assert typed_list[index] == expected_value
        # Test if a single value is returned as a list.
        name_path = NamePath([RegularName("main"), RegularName(value_name)])
        value = doc_single_values[name_path]
        typed_list = value.as_list(requested_type)
        assert isinstance(typed_list, list)
        assert len(typed_list) == 1
        # Provoke an error by using the method on a section (that will never match the requested type).
        value = doc_single_values["main"]
        with pytest.raises(ConfTypeMismatch):
            typed_list = value.as_list(requested_type)
        typed_list = value.as_list(requested_type, default=[42])
        assert typed_list == [42]
        # Expect an error for if one value has the wrong type.
        name_path = NamePath([RegularName("value_lists_with_wrong_type"), RegularName(value_name)])
        value = doc_single_values[name_path]
        with pytest.raises(ConfTypeMismatch):
            typed_list = value.as_list(requested_type)
        typed_list = value.as_list(requested_type, default=[42])
        assert typed_list == [42]
