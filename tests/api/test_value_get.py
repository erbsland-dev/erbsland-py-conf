#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import re
from pathlib import Path
from typing import Tuple

import pytest

from erbsland.conf.error import ConfValueNotFound
from erbsland.conf.parser import load
from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.value_type import ValueType
from erbsland.conf.error import ConfTypeMismatch
from erbsland.conf.name import RegularName, Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.time_delta import TimeUnit, TimeDelta
from erbsland.conf.value import Value


DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def doc_single_values():
    return load(DATA_DIR / "single_values.elcl")


class TestValueGet:

    def _key_from_value_name(
        self, doc, base_name, value_lookup, value_name, value_index
    ) -> Tuple[Value, str | NamePath | Name | int]:
        if value_lookup == "str":
            return doc, f"{base_name}.{value_name}"
        elif value_lookup == "name_path":
            return doc, NamePath([RegularName(base_name), RegularName(value_name)])
        elif value_lookup == "name":
            return doc[base_name], RegularName(value_name)
        elif value_lookup == "index":
            return doc[base_name], value_index
        else:
            raise ValueError(f"Unknown value_lookup: {value_lookup}")

    @pytest.mark.parametrize("value_lookup", ["str", "name_path", "name", "index"])
    @pytest.mark.parametrize(
        "method,value_name,value_index,expected",
        [
            pytest.param("get_int", "value_int", 0, 12345, id="int"),
            pytest.param("get_bool", "value_bool", 1, True, id="bool"),
            pytest.param("get_float", "value_float", 2, 12.345, id="float"),
            pytest.param("get_text", "value_text", 3, "This is Text", id="text"),
            pytest.param("get_date", "value_date", 4, datetime.date(2026, 8, 10), id="date"),
            pytest.param("get_time", "value_time", 5, Time(17, 54, second=12, tzinfo=datetime.timezone.utc), id="time"),
            pytest.param(
                "get_date_time",
                "value_date_time",
                6,
                DateTime(2026, 8, 10, hour=17, minute=54, second=12, tzinfo=datetime.timezone.utc),
                id="datetime",
            ),
            pytest.param("get_bytes", "value_bytes", 7, b"\x01\x02\x03\xfd\xfe\xff", id="bytes"),
            pytest.param("get_time_delta", "value_time_delta", 8, TimeDelta(10, TimeUnit.DAY), id="timedelta"),
            pytest.param("get_regex", "value_regex", 9, re.compile("regex"), id="regex"),
            pytest.param("get_value_list", "value_list", 10, [1, 2, 3], id="value_list"),
        ],
    )
    def test_get_named_type(self, doc_single_values, value_lookup, method, value_name, value_index, expected):
        value, key = self._key_from_value_name(doc_single_values, "main", value_lookup, value_name, value_index)
        m = getattr(value, method)
        assert callable(m)
        # Use without default-value.
        actual_native_value = m(key)
        if isinstance(actual_native_value, list):
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Use with a default.
        actual_native_value = m(key, default=42)
        if isinstance(actual_native_value, list):
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Error = wrong type
        value, key = self._key_from_value_name(
            doc_single_values, "main_with_wrong_type", value_lookup, value_name, value_index
        )
        m = getattr(value, method)
        with pytest.raises(ConfTypeMismatch):
            actual_native_value = m(key)
        actual_native_value = m(key, default=42)
        assert actual_native_value == 42
        # Error = value not found
        value, key = self._key_from_value_name(
            doc_single_values, "main_with_wrong_type", value_lookup, value_name + "X", value_index + 100
        )
        m = getattr(value, method)
        with pytest.raises(ConfValueNotFound):
            actual_native_value = m(key)
        actual_native_value = m(key, default=42)
        assert actual_native_value == 42

    @pytest.mark.parametrize("value_lookup", ["str", "name_path", "name", "index"])
    @pytest.mark.parametrize(
        "requested_type,value_name,value_index,expected",
        [
            pytest.param(int, "value_int", 0, 12345, id="int"),
            pytest.param(bool, "value_bool", 1, True, id="bool"),
            pytest.param(float, "value_float", 2, 12.345, id="float"),
            pytest.param(str, "value_text", 3, "This is Text", id="text"),
            pytest.param(datetime.date, "value_date", 4, datetime.date(2026, 8, 10), id="date"),
            pytest.param(Time, "value_time", 5, Time(17, 54, second=12, tzinfo=datetime.timezone.utc), id="time"),
            pytest.param(
                DateTime,
                "value_date_time",
                6,
                DateTime(2026, 8, 10, hour=17, minute=54, second=12, tzinfo=datetime.timezone.utc),
                id="datetime",
            ),
            pytest.param(bytes, "value_bytes", 7, b"\x01\x02\x03\xfd\xfe\xff", id="bytes"),
            pytest.param(TimeDelta, "value_time_delta", 8, TimeDelta(10, TimeUnit.DAY), id="timedelta"),
            pytest.param(re.Pattern, "value_regex", 9, re.compile("regex"), id="regex"),
            pytest.param(list, "value_list", 10, [1, 2, 3], id="value_list"),
        ],
    )
    def test_get_type(self, doc_single_values, value_lookup, requested_type, value_name, value_index, expected):
        value, key = self._key_from_value_name(doc_single_values, "main", value_lookup, value_name, value_index)
        # Use without default.
        actual_native_value = value.get_type(key, requested_type)
        if isinstance(actual_native_value, list):
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Use with a default.
        actual_native_value = value.get_type(key, requested_type, default=42)
        if isinstance(actual_native_value, list):
            for index, expected_value in enumerate(expected):
                assert actual_native_value[index].as_int() == expected_value
        else:
            assert actual_native_value == expected
            assert type(actual_native_value) == type(expected)
        # Error = wrong type
        value, key = self._key_from_value_name(
            doc_single_values, "main_with_wrong_type", value_lookup, value_name, value_index
        )
        with pytest.raises(ConfTypeMismatch):
            actual_native_value = value.get_type(key, requested_type)
        actual_native_value = value.get_type(key, requested_type, default=42)
        assert actual_native_value == 42
        # Error = value not found
        value, key = self._key_from_value_name(
            doc_single_values, "main_with_wrong_type", value_lookup, value_name + "X", value_index + 100
        )
        with pytest.raises(ConfValueNotFound):
            actual_native_value = value.get_type(key, requested_type)
        actual_native_value = value.get_type(key, requested_type, default=42)
        assert actual_native_value == 42

    @pytest.mark.parametrize("value_lookup", ["str", "name_path", "name", "index"])
    @pytest.mark.parametrize(
        "requested_type,value_name,value_index,expected",
        [
            pytest.param(int, "value_int", 0, [1, 2, 3, 4, 5], id="int"),
            pytest.param(bool, "value_bool", 1, [True, False, True], id="bool"),
            pytest.param(float, "value_float", 2, [1.1, 2.2, 3.3], id="float"),
            pytest.param(str, "value_text", 3, ["This is Text 1", "This is Text 2", "This is Text 3"], id="text"),
            pytest.param(
                datetime.date,
                "value_date",
                4,
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
                5,
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
                6,
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
                7,
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
                8,
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
                9,
                [
                    re.compile("regex1"),
                    re.compile("regex2"),
                    re.compile("regex3"),
                ],
                id="regex",
            ),
        ],
    )
    def test_get_list(self, doc_single_values, value_lookup, requested_type, value_name, value_index, expected):
        value, key = self._key_from_value_name(doc_single_values, "value_lists", value_lookup, value_name, value_index)
        # No default value
        typed_list = value.get_list(key, requested_type)
        assert isinstance(typed_list, list)
        assert len(typed_list) == len(expected)
        for index, expected_value in enumerate(expected):
            assert typed_list[index] == expected_value
        # With default value
        typed_list = value.get_list(key, requested_type, default=[42])
        assert isinstance(typed_list, list)
        assert len(typed_list) == len(expected)
        for index, expected_value in enumerate(expected):
            assert typed_list[index] == expected_value
        # Test if a single value is returned as a list.
        value, key = self._key_from_value_name(doc_single_values, "main", value_lookup, value_name, value_index)
        typed_list = value.get_list(key, requested_type)
        assert isinstance(typed_list, list)
        assert len(typed_list) == 1

        # Test value does not exist.
        value, key = self._key_from_value_name(
            doc_single_values, "value_lists", value_lookup, value_name + "X", value_index + 100
        )
        with pytest.raises(ConfValueNotFound):
            typed_list = value.get_list(key, requested_type)
        typed_list = value.as_list(requested_type, default=[42])
        assert typed_list == [42]
        # Test value is no list and has the wrong type.
        value, key = self._key_from_value_name(
            doc_single_values, "main_with_wrong_type", value_lookup, value_name, value_index
        )
        with pytest.raises(ConfTypeMismatch):
            typed_list = value.as_list(requested_type)
        typed_list = value.as_list(requested_type, default=[42])
        assert typed_list == [42]
        # Test value is list, but contains wrong type
        value, key = self._key_from_value_name(
            doc_single_values, "value_lists_with_wrong_type", value_lookup, value_name, value_index
        )
        with pytest.raises(ConfTypeMismatch):
            typed_list = value.as_list(requested_type)
        typed_list = value.as_list(requested_type, default=[42])
        assert typed_list == [42]
