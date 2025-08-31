#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from erbsland.conf.source import SourceIdentifier


def test_create_and_attributes():
    file_id = SourceIdentifier(SourceIdentifier.FILE, "config.elcl")
    assert file_id.name == "file"
    assert file_id.path == "config.elcl"

    text_id = SourceIdentifier(SourceIdentifier.TEXT, "")
    assert text_id.name == "text"
    assert text_id.path == ""


def test_equality_and_hash():
    id1 = SourceIdentifier(SourceIdentifier.FILE, "a.elcl")
    id2 = SourceIdentifier(SourceIdentifier.FILE, "a.elcl")
    id3 = SourceIdentifier(SourceIdentifier.FILE, "b.elcl")
    text_id = SourceIdentifier(SourceIdentifier.TEXT, "")

    assert id1 == id2
    assert id1 != id3
    assert id1 != text_id

    id_set = {id1, id2, id3}
    assert len(id_set) == 2


def test_string_representation():
    file_id = SourceIdentifier(SourceIdentifier.FILE, "path.elcl")
    assert str(file_id) == "file:path.elcl"

    text_id = SourceIdentifier(SourceIdentifier.TEXT, "")
    assert str(text_id) == "text:"


class CustomSourceIdentifier(SourceIdentifier):
    """Simple subclass used for exercising the SourceIdentifier interface."""


class TestCustomSourceIdentifier:
    """Tests for the SourceIdentifier methods using a subclass."""

    def test_str_and_repr(self):
        identifier = CustomSourceIdentifier("text", "doc")
        assert str(identifier) == "text:doc"
        assert repr(identifier) == "SourceIdentifier(text:doc)"

    @pytest.mark.parametrize(
        "name, path, expected",
        [
            pytest.param(
                SourceIdentifier.FILE,
                r"C:\\folder\\config.elcl",
                "file:config.elcl",
                id="compact-file-path",
            ),
            pytest.param(
                "memory",
                r"C:\\folder\\config.elcl",
                r"memory:C:\\folder\\config.elcl",
                id="compact-non-file",
            ),
        ],
    )
    def test_to_text_compact(self, name, path, expected):
        identifier = CustomSourceIdentifier(name, path)
        assert identifier.to_text(compact=True) == expected
