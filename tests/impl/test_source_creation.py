#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfIoError
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.source import SourceIdentifier


def test_file_source_from_string(tmp_path):
    file_path = tmp_path / "test.elcl"
    file_path.write_text("content")
    source = FileSource(str(file_path))

    assert source.identifier.name == SourceIdentifier.FILE
    assert source.identifier.path == file_path.resolve().as_posix()
    assert not source.is_open()

    source.open()
    assert source.is_open()
    assert source.readline() == "content"


def test_file_source_from_path(tmp_path):
    file_path = tmp_path / "data.elcl"
    file_path.write_text("line1\nline2")
    source = FileSource(file_path)

    assert source.identifier.name == SourceIdentifier.FILE
    assert source.identifier.path == file_path.resolve().as_posix()
    assert not source.is_open()

    source.open()
    assert source.readline() == "line1\n"


def test_text_source(tmp_path):
    source = TextSource("abc")

    assert source.identifier.name == SourceIdentifier.TEXT
    assert source.identifier.path == ""
    assert not source.is_open()

    source.open()
    assert source.is_open()
    assert source.readline() == "abc"


def test_file_source_non_existing_path(tmp_path):
    source = FileSource(tmp_path / "missing.elcl")
    with pytest.raises(ConfIoError):
        source.open()


def test_reading_closed_file_source(tmp_path):
    file_path = tmp_path / "data.elcl"
    file_path.write_text("line1\nline2")
    source = FileSource(file_path)
    source.open()
    source.close()
    with pytest.raises(ConfIoError):
        source.readline()


def test_reading_closed_text_source():
    source = TextSource("abc")
    source.open()
    source.close()
    with pytest.raises(ConfIoError):
        source.readline()


def test_file_source_invalid_path_type():
    with pytest.raises(TypeError):
        FileSource(123)


def test_text_source_invalid_text_type():
    with pytest.raises(TypeError):
        TextSource(123)
