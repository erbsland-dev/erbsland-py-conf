#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfNameConflict
from erbsland.conf.impl.document_impl import (
    DocumentBuilderImpl,
    DocumentImpl,
    create_value_object,
    validate_name_path_like,
    validate_value_to_add,
)
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.location import Location, Position
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.value_type import ValueType


def make_location() -> Location:
    return Location(SourceIdentifier(SourceIdentifier.TEXT, "test"), Position(1, 1))


class TestValidateHelpers:
    @pytest.mark.parametrize(
        "input_path, expected",
        [
            ("a.b", "a.b"),
            (Name.create_regular("c"), "c"),
            (NamePath.from_text("d"), "d"),
        ],
    )
    def test_validate_name_path_like_converts(self, input_path, expected):
        path = validate_name_path_like(input_path)
        assert isinstance(path, NamePath)
        assert path.to_text() == expected

    @pytest.mark.parametrize(
        "bad_path",
        [
            None,
            123,
            NamePath(),
            NamePath([Name.create_index(0)]),
            NamePath([Name.create_text_index(1)]),
            "[0]",
            '""[0]',
        ],
    )
    def test_validate_name_path_like_errors(self, bad_path):
        with pytest.raises(ValueError):
            validate_name_path_like(bad_path)

    def test_validate_value_to_add_allows_scalar(self):
        validate_value_to_add(1)

    @pytest.mark.parametrize(
        "value, msg",
        [
            (None, "Cannot add None"),
            ([], "Cannot add empty list"),
            ([1, object()], r"Value at \[1\] has an unsupported type"),
            ([[1], 2], r"Value at \[1\] is not a list"),
            ([[1], [object()]], r"Value at \[1\]\[0\] has an unsupported type"),
            (object(), "Unsupported value type to add"),
            ([1, 2], "Unsupported value type to add"),
            ([[1], [2]], "Unsupported value type to add"),
        ],
    )
    def test_validate_value_to_add_errors(self, value, msg):
        with pytest.raises(ValueError, match=msg):
            validate_value_to_add(value)

    def test_create_value_object_empty_list(self):
        obj = create_value_object([], NamePath.from_text("matrix"))
        assert obj.type is ValueType.VALUE_LIST
        assert len(obj) == 0

    def test_create_value_object_non_empty_list_raises(self):
        with pytest.raises(TypeError):
            create_value_object([1], NamePath.from_text("matrix"))

    def test_create_value_object_scalar(self):
        obj = create_value_object(5, NamePath.from_text("num"))
        assert obj.type is ValueType.INTEGER
        assert obj.name.as_text() == "num"


class TestDocumentImpl:
    def test_to_flat_dict_collects_all_values(self):
        doc = DocumentImpl()
        section_a = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("a"))
        value_b = ValueImpl(ValueType.INTEGER, Name.create_regular("b"), 1)
        section_a.add_child(value_b)
        section_x = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("x"))
        doc.add_child(section_a)
        doc.add_child(section_x)
        flat = doc.to_flat_dict()
        keys = {k.to_text() for k in flat}
        assert keys == {"a", "a.b", "x"}
        assert flat[NamePath.from_text("a.b")].native == 1


class TestDocumentBuilderImpl:
    def test_init_with_location(self):
        loc = make_location()
        builder = DocumentBuilderImpl(document_location=loc)
        doc = builder.get_document_and_reset()
        assert doc.location == loc

    def test_last_section_and_reset(self):
        builder = DocumentBuilderImpl()
        assert builder.last_section is None
        builder.add_section_map("root", None)
        assert builder.last_section is builder._document
        builder.reset()
        assert builder.last_section is None
        assert len(builder._document) == 0

    def test_add_section_map_converts_intermediate(self):
        builder = DocumentBuilderImpl()
        builder.add_section_map("a.b.c", None)
        builder.add_section_map("a.b", None)
        doc = builder.get_document_and_reset()
        assert doc["a.b"].type is ValueType.SECTION_WITH_NAMES

    def test_add_section_map_conflicts(self):
        builder = DocumentBuilderImpl()
        builder.add_section_map('alpha."beta"', None)
        with pytest.raises(ConfNameConflict):
            builder.add_section_map("alpha", None)
        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        builder.add_native_value("main.value", 1)
        with pytest.raises(ConfNameConflict):
            builder.add_section_map("main.value", None)

    def test_add_section_list_variants(self):
        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        with pytest.raises(ConfNameConflict):
            builder.add_section_list('main."text"', None)

        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        builder.add_section_list("main.server", None)
        first = builder.last_section
        builder.add_section_list("main.server", None)
        second = builder.last_section
        assert first != second
        doc = builder.get_document_and_reset()
        server_list = doc["main.server"]
        assert server_list.type is ValueType.SECTION_LIST
        assert len(server_list) == 2

        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        builder.add_section_map("main.server", None)
        with pytest.raises(ConfNameConflict):
            builder.add_section_list("main.server", None)

    def test_add_native_value(self):
        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        builder.add_native_value("main.port", 80)
        doc = builder.get_document_and_reset()
        assert doc["main.port"].native == 80
        builder = DocumentBuilderImpl()
        with pytest.raises(ValueError):
            builder.add_native_value("bad", None)

    def test_add_value_branching(self):
        builder = DocumentBuilderImpl()
        value = ValueImpl(ValueType.INTEGER, Name.create_regular("a"), 1)
        with pytest.raises(ConfNameConflict):
            builder.add_value(Name.create_regular("a"), value, None)

        builder.add_section_list("servers", None)
        value_name = ValueImpl(ValueType.TEXT, Name.create_regular("name"), "host1")
        builder.add_value("name", value_name, None)
        assert builder._document["servers"][0]["name"].native == "host1"

        builder.add_section_map("a.b.c", None)
        conflict_value = ValueImpl(ValueType.INTEGER, Name.create_regular("d"), 2)
        with pytest.raises(ConfNameConflict):
            builder.add_value("a.b.d", conflict_value, None)

        good_value = ValueImpl(ValueType.INTEGER, Name.create_regular("port"), 1)
        builder.add_value("a.b.c.port", good_value, None)
        with pytest.raises(ConfNameConflict):
            builder.add_value("a.b.c.port", ValueImpl(ValueType.INTEGER, Name.create_regular("port"), 2), None)

    def test_get_document_and_reset(self):
        builder = DocumentBuilderImpl()
        builder.add_section_map("main", None)
        doc = builder.get_document_and_reset()
        assert "main" in doc
        assert builder.last_section is None
        assert len(builder._document) == 0

    def test_resolve_existing_section(self):
        builder = DocumentBuilderImpl()
        with pytest.raises(ConfNameConflict):
            builder._resolve_existing_section(NamePath.from_text("a.b"), None)
        builder.add_section_map("main", None)
        builder.add_native_value("main.port", 1)
        with pytest.raises(ConfNameConflict):
            builder._resolve_existing_section(NamePath.from_text("main.port.x"), None)
        builder.add_section_list("servers", None)
        res = builder._resolve_existing_section(NamePath.from_text("servers.name"), None)
        assert res.name == Name.create_index(0)

    def test_get_or_create_parent_for_section(self):
        builder = DocumentBuilderImpl()
        path = NamePath([Name.create_regular("a"), Name.create_index(0), Name.create_regular("b")])
        with pytest.raises(ConfNameConflict):
            builder._get_or_create_parent_for_section(path, None)
        path = NamePath.from_text('x."text".y')
        with pytest.raises(ConfNameConflict):
            builder._get_or_create_parent_for_section(path, None)
        assert builder._document.get("x") is None
        builder.add_section_list("servers", None)
        parent = builder._get_or_create_parent_for_section(NamePath.from_text("servers.sub"), None)
        assert parent.name == Name.create_index(0)
        builder.add_section_map("main", None)
        builder.add_native_value("main.port", 1)
        with pytest.raises(ConfNameConflict):
            builder._get_or_create_parent_for_section(NamePath.from_text("main.port.sub"), None)
