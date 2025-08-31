#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest
from pathlib import Path

from erbsland.conf.error import (
    Error,
    ConfIoError,
    ConfEncodingError,
    ConfUnexpectedEnd,
    ConfCharacterError,
    ConfSyntaxError,
    ConfLimitExceeded,
    ConfNameConflict,
    ConfIndentationError,
    ConfUnsupportedError,
    ConfSignatureError,
    ConfAccessError,
    ConfValidationError,
    ConfInternalError,
    ErrorCategory,
    ConfValueNotFound,
    ConfTypeMismatch,
    ErrorOutput,
)
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.location import Location, Position
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.name_path import NamePath


def test_error_source_identifier_creates_location():
    src = SourceIdentifier(SourceIdentifier.FILE, "/tmp/data.elcl")
    err = Error(ErrorCategory.IO, "failure", source=src)
    assert isinstance(err.location, Location)
    assert err.location.source_identifier == src
    assert err.path is None
    assert err.system_message is None


def test_error_source_creates_location():
    src = TextSource("text")
    err = Error(ErrorCategory.IO, "failure", source=src)
    assert isinstance(err.location, Location)
    assert err.location.source_identifier == src.identifier
    assert err._path is None
    assert err._system_message is None


def test_error_location_path_system_message():
    loc_src = SourceIdentifier(SourceIdentifier.TEXT, "")
    loc = Location(loc_src)
    path = Path("/tmp/file")
    system_message = "permission denied"
    err = Error(
        ErrorCategory.SYNTAX,
        "error",
        source=loc,
        path=path,
        system_message=system_message,
    )
    assert err._source is loc
    assert err._path == path
    assert err._system_message == system_message


@pytest.mark.parametrize(
    "cls, category",
    [
        (ConfIoError, ErrorCategory.IO),
        (ConfEncodingError, ErrorCategory.ENCODING),
        (ConfUnexpectedEnd, ErrorCategory.UNEXPECTED_END),
        (ConfCharacterError, ErrorCategory.CHARACTER),
        (ConfSyntaxError, ErrorCategory.SYNTAX),
        (ConfLimitExceeded, ErrorCategory.LIMIT_EXCEEDED),
        (ConfNameConflict, ErrorCategory.NAME_CONFLICT),
        (ConfIndentationError, ErrorCategory.INDENTATION),
        (ConfUnsupportedError, ErrorCategory.UNSUPPORTED),
        (ConfSignatureError, ErrorCategory.SIGNATURE),
        (ConfAccessError, ErrorCategory.ACCESS),
        (ConfValidationError, ErrorCategory.VALIDATION),
        (ConfInternalError, ErrorCategory.INTERNAL),
        (ConfValueNotFound, ErrorCategory.VALUE_NOT_FOUND),
        (ConfTypeMismatch, ErrorCategory.TYPE_MISMATCH),
    ],
)
def test_error_subclass_categories(cls, category):
    err = cls("msg")
    assert err.category == category


def test_error_optional_parameters(tmp_path):
    src_id = SourceIdentifier(SourceIdentifier.FILE, (tmp_path / "src.elcl").as_posix())
    pos = Position(1, 2)
    path = tmp_path / "data" / "file.txt"
    name_path = NamePath.from_text("root.value")
    err = Error(
        ErrorCategory.SYNTAX,
        "problem",
        source=src_id,
        position=pos,
        path=path,
        system_message="denied",
        name_path=name_path,
        offset=3,
    )
    assert err.location == Location(src_id, pos.with_offset(3))
    assert err.path == path
    assert err.system_message == "denied"
    assert err.name_path == name_path
    assert err._offset == 3


def test_error_offset_without_source():
    err = Error(ErrorCategory.IO, "failure", offset=5)
    assert err.location is None
    assert err._offset == 5


@pytest.mark.parametrize(
    "factory, message",
    [
        pytest.param(lambda: Error("bad", "msg"), "'category' must be an ErrorCategory object", id="category"),
        pytest.param(lambda: Error(ErrorCategory.IO, 1), "'message' must be a string", id="message"),
        pytest.param(
            lambda: Error(ErrorCategory.IO, "msg", source=object()),
            "'source' must be a Source, SourceIdentifier or Location object",
            id="source",
        ),
        pytest.param(
            lambda: Error(
                ErrorCategory.IO,
                "msg",
                source=SourceIdentifier(SourceIdentifier.FILE, "p"),
                position=object(),
            ),
            "'position' must be a Position object",
            id="position",
        ),
        pytest.param(lambda: Error(ErrorCategory.IO, "msg", path="p"), "'path' must be a Path object.", id="path"),
        pytest.param(
            lambda: Error(ErrorCategory.IO, "msg", system_message=object()),
            "'system_message' must be a string",
            id="system_message",
        ),
        pytest.param(
            lambda: Error(ErrorCategory.IO, "msg", offset="1"),
            "'offset' must be an integer",
            id="offset",
        ),
    ],
)
def test_error_invalid_types(factory, message):
    with pytest.raises(ValueError) as exc_info:
        factory()
    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    "category, code",
    [
        (ErrorCategory.IO, 1),
        (ErrorCategory.ENCODING, 2),
        (ErrorCategory.UNEXPECTED_END, 3),
        (ErrorCategory.CHARACTER, 4),
        (ErrorCategory.SYNTAX, 5),
        (ErrorCategory.LIMIT_EXCEEDED, 6),
        (ErrorCategory.NAME_CONFLICT, 7),
        (ErrorCategory.INDENTATION, 8),
        (ErrorCategory.UNSUPPORTED, 9),
        (ErrorCategory.SIGNATURE, 10),
        (ErrorCategory.ACCESS, 11),
        (ErrorCategory.VALIDATION, 12),
        (ErrorCategory.INTERNAL, 99),
        (ErrorCategory.VALUE_NOT_FOUND, 101),
        (ErrorCategory.TYPE_MISMATCH, 102),
    ],
)
def test_error_code_property(category, code):
    err = Error(category, "msg")
    assert err.code == code


def test_error_message_property():
    err = Error(ErrorCategory.IO, "read failed")
    assert err.message == "read failed"
    assert str(err) == "read failed"


def test_error_to_text_filename_only(tmp_path):
    src_file = tmp_path / "dir" / "input.elcl"
    src_id = SourceIdentifier(SourceIdentifier.FILE, src_file.as_posix())
    loc = Location(src_id, Position(1, 2))
    path = tmp_path / "other" / "file.txt"
    err = Error(ErrorCategory.IO, "boom", source=loc, path=path)
    text = err.to_text(ErrorOutput.FILENAME_ONLY)
    assert text == f"boom, source=file:{src_file.name}:[1:2], path={path.name}"


def test_error_to_text_use_lines(tmp_path):
    src_file = tmp_path / "a" / "b" / "input.elcl"
    src_id = SourceIdentifier(SourceIdentifier.FILE, src_file.as_posix())
    loc = Location(src_id, Position(1, 2))
    path = tmp_path / "x" / "y.txt"
    name_path = NamePath.from_text("foo.bar")
    err = Error(
        ErrorCategory.IO,
        "oops",
        source=loc,
        path=path,
        system_message="err",
        name_path=name_path,
    )
    text = err.to_text(ErrorOutput.USE_LINES)
    expected = (
        "oops\n"
        f"    source: file:{src_file.as_posix()}:[1:2]\n"
        f"    path: {path.as_posix()}\n"
        "    system error: err\n"
        "    name-path: foo.bar"
    )
    assert text == expected
