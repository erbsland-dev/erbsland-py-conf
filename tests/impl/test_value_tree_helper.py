#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.impl.document_impl import DocumentImpl
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.impl.value_tree_helper import ValueTreeHelper
from erbsland.conf.location import Location, Position
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.test_output import TestOutput
from erbsland.conf.value_type import ValueType


class DummyValue:
    is_root = False
    type = ValueType.TEXT
    name_path = NamePath([])


def _build_complex_tree() -> DocumentImpl:
    root = DocumentImpl()

    sid1 = SourceIdentifier(SourceIdentifier.FILE, "/tmp/file1")
    sid2 = SourceIdentifier(SourceIdentifier.FILE, "/tmp/file2")
    loc1 = Location(sid1, Position(1, 1))
    loc2 = Location(sid1, Position(2, 1))
    loc3 = Location(sid2, Position(3, 1))

    first = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("first"), location=loc1)
    root.add_child(first)
    first.add_child(ValueImpl(ValueType.TEXT, Name.create_regular("inner"), "text"))

    root.add_child(ValueImpl(ValueType.TEXT, Name.create_regular("second"), "value2", loc2))

    third = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_regular("third"), location=loc3)
    root.add_child(third)
    third.add_child(ValueImpl(ValueType.TEXT, Name.create_regular("inner"), "more"))

    return root


def _build_simple_tree() -> DocumentImpl:
    root = DocumentImpl()
    sid = SourceIdentifier(SourceIdentifier.FILE, "/tmp/simple")
    loc = Location(sid, Position(1, 2))
    root.add_child(ValueImpl(ValueType.TEXT, Name.create_regular("child"), "x", loc))
    return root


def test_init_raises_type_error_on_non_value():
    with pytest.raises(TypeError):
        ValueTreeHelper(123)  # type: ignore[arg-type]


def test_compute_name_handles_empty_path():
    assert ValueTreeHelper._compute_name(DummyValue()) == "<Empty>"


def test_append_source_identifier_max_index():
    root = DocumentImpl()
    sid = SourceIdentifier(SourceIdentifier.FILE, "/tmp/file")
    loc = Location(sid, Position(1, 1))
    value = ValueImpl(ValueType.TEXT, Name.create_regular("v"), "x", loc)
    helper = ValueTreeHelper(root, TestOutput.SOURCE_ID)
    helper._label_index = 60
    label = helper._append_source_identifier(value)
    assert label == "z:"
    assert helper._label_index == 60


def test_render_without_position_or_source():
    root = _build_complex_tree()
    lines = ValueTreeHelper(root).render()
    assert lines == [
        "<Document> => Document()",
        "├───first => SectionWithNames()",
        '│   └───inner => Text("text")',
        '├───second => Text("value2")',
        "└───third => SectionWithNames()",
        '    └───inner => Text("more")',
    ]


def test_render_with_alignment_and_labels():
    root = _build_complex_tree()
    helper = ValueTreeHelper(root, TestOutput.SOURCE_ID | TestOutput.POSITION | TestOutput.ALIGN_VALUES)
    lines = helper.render()
    assert lines == [
        "<Document>    => Document()[no source:undefined]",
        "├───first     => SectionWithNames()[A:1:1]",
        '│   └───inner => Text("text")[no source:undefined]',
        '├───second    => Text("value2")[A:2:1]',
        "└───third     => SectionWithNames()[B:3:1]",
        '    └───inner => Text("more")[no source:undefined]',
        "A: file:/tmp/file1",
        "B: file:/tmp/file2",
    ]


def test_render_only_position():
    root = _build_simple_tree()
    lines = ValueTreeHelper(root, TestOutput.POSITION).render()
    assert lines == [
        "<Document> => Document()[undefined]",
        '└───child => Text("x")[1:2]',
    ]


def test_render_only_source_identifier():
    root = _build_simple_tree()
    lines = ValueTreeHelper(root, TestOutput.SOURCE_ID).render()
    assert lines == [
        "<Document> => Document()[no source:]",
        '└───child => Text("x")[A:]',
        "A: file:/tmp/simple",
    ]
