#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime as dt
import pickle
import re

import pytest

from erbsland.conf.datetime import DateTime, Time
from erbsland.conf.error import ConfNameConflict, ConfSyntaxError, ConfTypeMismatch, ConfValueNotFound
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.test_output import TestOutput
from erbsland.conf.time_delta import TimeDelta, TimeUnit
from erbsland.conf.value_type import ValueType
from erbsland.conf.impl.value_impl import _name_path_from_key


def make_location() -> Location:
    return Location(SourceIdentifier("test", "path"))


class TestValueImpl:
    def test_constructor_errors(self):
        name = Name.create_regular("a")
        location = make_location()
        with pytest.raises(ValueError, match="'value_type' must be a ValueType"):
            ValueImpl("bad", name)
        with pytest.raises(ValueError, match="'name' must be set for non-root values"):
            ValueImpl(ValueType.INTEGER, None)
        with pytest.raises(ValueError, match="'name' must be a Name"):
            ValueImpl(ValueType.INTEGER, "name")
        with pytest.raises(ValueError, match="Invalid type for value"):
            ValueImpl(ValueType.INTEGER, name, object())
        with pytest.raises(ValueError, match="'location' must be a Location"):
            ValueImpl(ValueType.INTEGER, name, 1, location="loc")
        root = ValueImpl(ValueType.DOCUMENT, None)
        child = ValueImpl(ValueType.INTEGER, name, 1, location)
        assert root.type is ValueType.DOCUMENT
        assert child.native == 1

    def test_from_data(self):
        name = Name.create_regular("a")
        loc = make_location()
        with pytest.raises(ValueError, match="'name' must be a Name"):
            ValueImpl.from_data("bad", 1)
        with pytest.raises(ValueError, match="Invalid type for value"):
            ValueImpl.from_data(name, object())
        with pytest.raises(ValueError, match="'location' must be a Location"):
            ValueImpl.from_data(name, 1, location="loc")
        val = ValueImpl.from_data(name, 1, loc)
        assert val.type is ValueType.INTEGER
        assert val.name == name

    def test_properties_and_name_path(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        child = ValueImpl(ValueType.INTEGER, Name.create_regular("child"), 5)
        root.add_child(child)
        assert child.parent is root
        assert child.has_parent
        assert root.is_root
        assert child.name_path == NamePath.from_text("child")
        new_name = Name.create_regular("renamed")
        child.name = new_name
        assert child.name == new_name
        with pytest.raises(AssertionError):
            child.name = "x"  # type: ignore[assignment]
        new_loc = make_location()
        child.location = new_loc
        assert child.location == new_loc

    def test_add_child_conflicts(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        child = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        root.add_child(child)
        with pytest.raises(ValueError):
            root.add_child(child)
        with pytest.raises(ValueError):
            root.add_child(ValueImpl(ValueType.DOCUMENT, None))
        section_texts = ValueImpl(ValueType.SECTION_WITH_TEXTS, Name.create_regular("sec"))
        with pytest.raises(ConfNameConflict):
            section_texts.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("x"), 1))
        section = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("sec"))
        section.add_child(ValueImpl(ValueType.INTEGER, Name.create_text("txt"), 1))
        assert section.type is ValueType.SECTION_WITH_TEXTS
        section2 = ValueImpl(ValueType.DOCUMENT, None)
        section2.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1))
        with pytest.raises(ConfNameConflict):
            section2.add_child(ValueImpl(ValueType.INTEGER, Name.create_text("t"), 1))
        vlist = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("list"))
        with pytest.raises(ConfNameConflict):
            vlist.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("x"), 1))
        vlist.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(0), 1))
        slist = ValueImpl(ValueType.SECTION_LIST, Name.create_regular("slist"))
        with pytest.raises(ConfNameConflict):
            slist.add_child(ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("x")))
        slist.add_child(ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_index(0)))
        inter = ValueImpl(ValueType.INTERMEDIATE_SECTION, Name.create_regular("inter"))
        with pytest.raises(ConfNameConflict):
            inter.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("x"), 1))
        inter.add_child(ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("sec")))
        with pytest.raises(ConfNameConflict):
            inter.add_child(ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_text("txt")))
        single = ValueImpl(ValueType.INTEGER, Name.create_regular("single"), 1)
        with pytest.raises(ConfNameConflict):
            single.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("x"), 1))

    def test_remove_child(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        child = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        root.add_child(child)
        root.remove_child(child.name)
        assert len(root) == 0
        assert child.parent is None

    def test_child_access(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        child = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        root.add_child(child)
        list_parent = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("list"))
        sub_child = ValueImpl(ValueType.INTEGER, Name.create_index(0), 2)
        list_parent.add_child(sub_child)
        root.add_child(list_parent)
        assert root[0] is child
        with pytest.raises(ConfValueNotFound):
            root[5]
        assert root["a"] is child
        assert root[Name.create_regular("a")] is child
        assert root[NamePath.from_text("list[0]")] is sub_child
        with pytest.raises(ConfValueNotFound):
            root["b"]
        with pytest.raises(ConfSyntaxError):
            root["["]
        assert root.get("missing", 7) == 7
        assert root.get("a") is child
        assert "a" in root
        assert "missing" not in root
        assert list(iter(root)) == [child, list_parent]
        assert len(root) == 2
        assert root.first is child
        assert root.last is list_parent
        empty = ValueImpl(ValueType.DOCUMENT, None)
        with pytest.raises(ConfValueNotFound):
            _ = empty.first
        with pytest.raises(ConfValueNotFound):
            _ = empty.last

    def test_as_type_and_as_list(self):
        v_int = ValueImpl(ValueType.INTEGER, Name.create_regular("i"), 1)
        assert v_int.as_type(int) == 1
        with pytest.raises(ConfTypeMismatch):
            v_int.as_type(float)
        assert v_int.as_type(float, default=0.0) == 0.0
        list_value = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("l"))
        list_value.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(0), 1))
        list_value.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(1), 2))
        assert list_value.as_type(list) == list_value._children
        assert v_int.as_list(int) == [1]
        assert list_value.as_list(int) == [1, 2]
        list_value.add_child(ValueImpl(ValueType.BOOLEAN, Name.create_index(2), True))
        with pytest.raises(ConfTypeMismatch):
            list_value.as_list(int)
        assert list_value.as_list(int, default=[]) == []
        other = ValueImpl(ValueType.FLOAT, Name.create_regular("f"), 1.2)
        with pytest.raises(ConfTypeMismatch):
            other.as_list(int)
        assert other.as_list(int, default=None) is None
        with pytest.raises(ValueError):
            v_int.as_list(list)
        with pytest.raises(ValueError):
            v_int.as_type(dict)

    def test_get_type_and_get_list(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        int_child = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        root.add_child(int_child)
        assert root.get_type("a", int) == 1
        assert root.get_type("missing", int, default=5) == 5
        with pytest.raises(ConfValueNotFound):
            root.get_type("missing", int)
        float_child = ValueImpl(ValueType.FLOAT, Name.create_regular("b"), 2.0)
        root.add_child(float_child)
        with pytest.raises(ConfTypeMismatch):
            root.get_type("b", int)
        assert root.get_type("b", int, default=0) == 0
        list_parent = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("list"))
        list_parent.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(0), 1))
        list_parent.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(1), 2))
        root.add_child(list_parent)
        assert root.get_list("list", int) == [1, 2]
        assert root.get_list("list", float, default=[]) == []
        with pytest.raises(ConfTypeMismatch):
            root.get_list("list", float)

    def test_convert_to(self):
        v = ValueImpl(ValueType.TEXT, Name.create_regular("t"), "123")
        assert v.convert_to(int) == 123
        assert v.convert_to(float) == pytest.approx(123.0)
        assert v.convert_to(bool) is True
        assert v.convert_to(str) == "123"
        dt_val = ValueImpl(
            ValueType.DATE_TIME, Name.create_regular("dt"), DateTime(2020, 1, 2, hour=3, minute=4, second=5)
        )
        assert dt_val.convert_to(dt.date) == dt.date(2020, 1, 2)
        assert dt_val.convert_to(Time) == Time(3, 4, second=5)
        text_time = ValueImpl(ValueType.TEXT, Name.create_regular("time"), "04:05:06")
        assert text_time.convert_to(Time) == Time.fromisoformat("04:05:06")
        text_date = ValueImpl(ValueType.TEXT, Name.create_regular("date"), "2020-02-03")
        assert text_date.convert_to(dt.date) == dt.date(2020, 2, 3)
        invalid_date = ValueImpl(ValueType.TEXT, Name.create_regular("bad"), "x")
        assert invalid_date.convert_to(dt.date) == dt.date(1970, 1, 1)
        bytes_val = ValueImpl(ValueType.INTEGER, Name.create_regular("b"), 5)
        assert bytes_val.convert_to(bytes) == b"5"
        regex_val = ValueImpl(ValueType.INTEGER, Name.create_regular("r"), 5)
        assert regex_val.convert_to(re.Pattern).pattern == "5"
        list_val = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("l"))
        list_val.add_child(ValueImpl(ValueType.INTEGER, Name.create_index(0), 1))
        assert list_val.convert_to(list) == list_val._children
        single = ValueImpl(ValueType.INTEGER, Name.create_regular("s"), 2)
        assert single.convert_to(list) is single
        assert single.convert_to(TimeDelta) is None
        with pytest.raises(ValueError):
            single.convert_to(dict)

    @pytest.mark.parametrize(
        "value,expected",
        [
            pytest.param(ValueImpl(ValueType.INTEGER, Name.create_regular("i"), 1), "Integer(1)", id="int"),
            pytest.param(ValueImpl(ValueType.BOOLEAN, Name.create_regular("b"), True), "Boolean(true)", id="bool"),
            pytest.param(ValueImpl(ValueType.FLOAT, Name.create_regular("f"), 1.25), "Float(1.25)", id="float"),
            pytest.param(ValueImpl(ValueType.TEXT, Name.create_regular("t"), "a"), 'Text("a")', id="text"),
            pytest.param(
                ValueImpl(ValueType.DATE, Name.create_regular("d"), dt.date(2020, 1, 2)), "Date(2020-01-02)", id="date"
            ),
            pytest.param(
                ValueImpl(ValueType.TIME, Name.create_regular("time"), Time(1, 2)), "Time(01:02:00)", id="time"
            ),
            pytest.param(
                ValueImpl(
                    ValueType.DATE_TIME, Name.create_regular("dt"), DateTime(2020, 1, 2, hour=3, minute=4, second=5)
                ),
                "DateTime(2020-01-02 03:04:05)",
                id="datetime",
            ),
            pytest.param(ValueImpl(ValueType.BYTES, Name.create_regular("bytes"), b"ab"), "Bytes(6162)", id="bytes"),
            pytest.param(
                ValueImpl(ValueType.TIME_DELTA, Name.create_regular("td"), TimeDelta(1, TimeUnit.SECOND)),
                "TimeDelta(1,second)",
                id="timedelta",
            ),
            pytest.param(
                ValueImpl(ValueType.REGEX, Name.create_regular("re"), re.compile("a")),
                'RegEx("a")',
                id="regex",
            ),
        ],
    )
    def test_to_test_text(self, value, expected):
        assert value.to_test_text() == expected

    def test_to_test_text_container_and_tree(self):
        container = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("c"))
        container.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1))
        assert container.to_test_text(TestOutput.CONTAINER_SIZE) == "SectionWithNames(size=1)"
        assert container.to_test_text() == "SectionWithNames()"
        tree = container.to_test_value_tree(TestOutput.CONTAINER_SIZE)
        assert "SectionWithNames(size=1)" in tree
        assert "Integer(1)" in tree

    def test_pickling(self):
        root = ValueImpl(ValueType.DOCUMENT, None)
        section = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("sec"))
        item = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        section.add_child(item)
        root.add_child(section)
        blob = pickle.dumps(root)
        clone = pickle.loads(blob)
        sec_clone = clone["sec"]
        assert sec_clone["a"].native == 1
        assert sec_clone.parent is clone
        state = root.__getstate__()
        state["_v"] = 0
        clone2 = object.__new__(ValueImpl)
        with pytest.raises(ValueError):
            clone2.__setstate__(state)

    @pytest.mark.parametrize(
        "value,expected",
        [
            pytest.param(
                ValueImpl(ValueType.TEXT, Name.create_regular("t"), "\n"),
                'Text(name=t, data="\\n")',
                id="text",
            ),
            pytest.param(
                ValueImpl(ValueType.INTEGER, Name.create_regular("i"), 1),
                "Integer(name=i, data=1)",
                id="int",
            ),
            pytest.param(
                (lambda v: (v.add_child(ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)), v)[1])(
                    ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("sec"))
                ),
                "SectionWithNames(name=sec, size=1)",
                id="container",
            ),
        ],
    )
    def test_str_branches(self, value, expected):
        assert str(value) == expected

    def test_child_for_name_edge_cases(self):
        simple = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        assert simple._child_for_name(Name.create_regular("b")) is None

        section = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("s"))
        assert section._child_for_name(Name.create_index(0)) is None

        vlist = ValueImpl(ValueType.VALUE_LIST, Name.create_regular("l"))
        assert vlist._child_for_name(Name.create_index(1)) is None
        assert vlist._child_for_name(Name.create_regular("a")) is None

    def test_to_test_text_minimal_escape(self):
        text_val = ValueImpl(ValueType.TEXT, Name.create_regular("t"), "\n")
        assert text_val.to_test_text(TestOutput.MINIMAL_ESC) == 'Text("\\n")'
        regex_val = ValueImpl(ValueType.REGEX, Name.create_regular("r"), re.compile("\n"))
        assert regex_val.to_test_text(TestOutput.MINIMAL_ESC) == 'RegEx("\\n")'

    def test_test_text_content_default_case(self):
        class DummyType:
            value = "Dummy"

            @staticmethod
            def is_container() -> bool:
                return False

        v = ValueImpl(ValueType.INTEGER, Name.create_regular("d"), 1)
        v._type = DummyType()
        v._data = None
        assert v._test_text_content(TestOutput.DEFAULT) == ""

    def test_convert_text_to_datetime(self):
        text_dt = ValueImpl(ValueType.TEXT, Name.create_regular("dt"), "2020-02-03T04:05:06")
        assert text_dt.convert_to(DateTime) == DateTime.fromisoformat("2020-02-03T04:05:06")

    def test_convert_section_list_to_list(self):
        section_list = ValueImpl(ValueType.SECTION_LIST, Name.create_regular("sl"))
        entry = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_index(0))
        section_list.add_child(entry)
        result = section_list.convert_to(list)
        assert result == [entry]
        assert result is not section_list._children
