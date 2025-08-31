#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.document import Document
from erbsland.conf.error import ConfTypeMismatch
from erbsland.conf.impl.document_impl import DocumentImpl
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.name import Name
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType


class TestValueBasics:

    @staticmethod
    def _make_value(value_type: ValueType, data) -> Value:
        name = Name.create_regular("test")
        return ValueImpl(value_type, name, data)

    @staticmethod
    def _make_nested_section_lists() -> Document:
        doc = DocumentImpl()
        section_list = ValueImpl(ValueType.SECTION_LIST, Name.create_regular("list"))
        doc.add_child(section_list)
        nested_values = iter(["d", "e", "f", "g", "h", "i", "j", "k", "l"])
        for index, text in enumerate(["a", "b", "c"]):
            section_list_entry = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_index(index))
            section_list.add_child(section_list_entry)
            value = ValueImpl(ValueType.TEXT, Name.create_regular("value"), text)
            section_list_entry.add_child(value)
            sub_section_list = ValueImpl(ValueType.SECTION_LIST, Name.create_regular("sub_list"))
            section_list_entry.add_child(sub_section_list)
            for sub_index in range(3):
                sub_section_list_entry = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_index(sub_index))
                sub_section_list.add_child(sub_section_list_entry)
                value = ValueImpl(ValueType.TEXT, Name.create_regular("value"), next(nested_values))
                sub_section_list_entry.add_child(value)
        return doc

    def test_as_int_matches_type(self):
        value = self._make_value(ValueType.INTEGER, 7)
        assert value.as_int() == 7

    def test_as_int_raises_type_mismatch_without_default(self):
        value = self._make_value(ValueType.FLOAT, 3.14)
        with pytest.raises(ConfTypeMismatch):
            value.as_int()

    def test_as_int_returns_default_on_mismatch(self):
        value = self._make_value(ValueType.FLOAT, 3.14)
        assert value.as_int(default=0) == 0

    def test_as_bool_with_default(self):
        value = self._make_value(ValueType.INTEGER, 1)
        assert value.as_bool(default=False) is False
        with pytest.raises(ConfTypeMismatch):
            value.as_bool()

    @pytest.mark.parametrize(
        "name_path, expected_text",
        [
            ("list[0].value", "a"),
            ("list[1].value", "b"),
            ("list[2].value", "c"),
            ("list.value", "c"),
            ("list[0].sub_list[0].value", "d"),
            ("list[0].sub_list[1].value", "e"),
            ("list[0].sub_list[2].value", "f"),
            ("list[1].sub_list[0].value", "g"),
            ("list[1].sub_list[1].value", "h"),
            ("list[1].sub_list[2].value", "i"),
            ("list[2].sub_list[0].value", "j"),
            ("list[2].sub_list[1].value", "k"),
            ("list[2].sub_list[2].value", "l"),
            ("list.sub_list[0].value", "j"),
            ("list.sub_list[1].value", "k"),
            ("list.sub_list[2].value", "l"),
            ("list.sub_list.value", "l"),
            ("list[0].sub_list.value", "f"),
            ("list[1].sub_list.value", "i"),
            ("list[2].sub_list.value", "l"),
        ],
    )
    def test_last_element_in_section_list_handling(self, name_path, expected_text):
        doc = self._make_nested_section_lists()
        value = doc[name_path]
        assert value.type == ValueType.TEXT
        assert value.as_text() == expected_text
        value = doc.get(name_path)
        assert value.type == ValueType.TEXT
        assert value.as_text() == expected_text
