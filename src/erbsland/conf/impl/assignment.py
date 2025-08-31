#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Generator, NoReturn, Tuple

from erbsland.conf.error import (
    ConfSyntaxError,
    ConfInternalError,
    ConfUnexpectedEnd,
    ConfUnsupportedError,
    ConfLimitExceeded,
    Error,
)
from erbsland.conf.impl.features import SUPPORTED_FEATURES
from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.impl.value_storage_type import ValueStorageType
from erbsland.conf.location import Location
from erbsland.conf.name import (
    Name,
    META_NAME_VERSION,
    META_NAME_FEATURES,
    META_NAME_SIGNATURE,
    META_NAME_INCLUDE,
    META_NAMES,
    NameType,
)
from erbsland.conf.name_path import NamePath
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.value_type import ValueType


class AssignmentType(enum.Enum):
    """Kinds of assignments produced while parsing a document."""

    END_OF_DOCUMENT = enum.auto()
    SECTION_MAP = enum.auto()
    SECTION_LIST = enum.auto()
    VALUE = enum.auto()
    META_VALUE = enum.auto()


@dataclass(frozen=True, slots=True)
class Assignment:
    """
    Representation of a single assignment in the configuration file.

    Fields:
    * `type`: The kind of assignment.
    * `name_path`: Points to the name being assigned.
    * `location`: Refers to the position of the assignment, usually the name or the opening bracket of a section.
    * `value`: Holds the assigned value, only for `AssignmentType.VALUE` assignments.
    """

    type: AssignmentType = AssignmentType.END_OF_DOCUMENT
    name_path: NamePath | None = None
    location: Location | None = None
    value: ValueImpl | None = None

    def is_end_of_document(self) -> bool:
        return self.type == AssignmentType.END_OF_DOCUMENT

    def __str__(self) -> str:
        return f"Assignment(type={self.type.name}, name_path={self.name_path}, location={self.location}, value={self.value})"


# Generator type for the assignment stream.
AssignmentGenerator = Generator[Assignment, None, None]


class AssignmentStream:
    """
    Generate assignments from lexer tokens.

    The assignment stream validates if the tokens received from the lexer form correct assignments, yet most low-level
    error handling happens in the lexer. Expectations, what the lexer shall verify are expressed with ``assert``
    statements to catch any errors introduced on the lexer side.

    The logical structure of the assignments is not validated. The stream does not check if the assignments form a
    valid tree or if there are name conflicts. What this implementation does is checking if multiple tokens
    actually form valid values or sections for the assignments.

    The stream also validates the meta-values ``@version`` and ``@features``, if their values are valid and if
    they are not duplicated.

    The main loop raises an internal error if the lexer reports an unexpected token. This case should never happen
    and is a bug in the lexer.
    """

    def __init__(self, lexer: Lexer, source_identifier: SourceIdentifier):
        """Initialize the stream.

        :param lexer: Lexer providing tokens.
        :param source_identifier: Identifier of the source being parsed.
        """

        self._lexer = lexer
        self._source_identifier = source_identifier
        self._current_absolute_name_path: NamePath | None = None  # The last absolute name path.
        self._current_name_path: NamePath | None = None  # The logical name path for value assignments.
        self._token_generator = lexer.tokens()
        self._token: Token = Token(TokenType.END_OF_DATA)
        self._last_token: Token | None = None
        self._in_document_root = True  # If we are in the document root (no section was read yet)
        self._read_meta_version = False
        self._read_meta_features = False

    def assignments(self) -> AssignmentGenerator:
        """Yield assignments from the underlying token stream."""

        self._next_non_spacing_token()
        while self._token.type != TokenType.END_OF_DATA:
            match self._token.type:
                case TokenType.SPACING | TokenType.INDENTATION | TokenType.LINE_BREAK | TokenType.COMMENT:
                    self._next_non_spacing_token()  # Skip spacing and comments and empty lines.
                case TokenType.NAME:
                    yield self._handle_value()
                case TokenType.SECTION_MAP_OPEN | TokenType.SECTION_LIST_OPEN:
                    yield self._handle_section()
                case _:
                    self._internal_error(f"Unexpected expression at this point in the document.")
        yield Assignment()  # End of document mark
        return

    def _location(self, *, last=False) -> Location:
        """Get the location of the current token or the last token if last is True."""

        token = self._last_token if last else self._token
        if token and token.begin is not None:
            location = Location(self._source_identifier, token.begin)
        else:
            location = Location(self._source_identifier)
        return location

    def _syntax_error(self, message: str) -> NoReturn:
        """Raise a syntax error with the given message and location."""

        raise ConfSyntaxError(message, source=self._location())

    def _unsupported(self, message: str) -> NoReturn:
        """Raise an unsupported error with the given message and location."""

        raise ConfUnsupportedError(message, source=self._location())

    def _unexpected_end(self, message: str) -> NoReturn:
        """Raise an unexpected end error with the given message and location."""

        raise ConfUnexpectedEnd(message, source=self._location(last=True))

    def _internal_error(self, message: str) -> NoReturn:
        """Raise an internal error with the given message and location."""

        raise ConfInternalError(message, source=self._location())

    def _next_token(self):
        """Advance to the next token."""

        self._last_token = self._token
        self._token = next(self._token_generator, None)
        if self._token is None:
            self._token = Token(TokenType.END_OF_DATA)

    def _next_non_spacing_token(self):
        """Advance to the next non-spacing token."""

        self._next_token()
        while self._token.type in (TokenType.SPACING, TokenType.COMMENT):
            self._next_token()

    def _expect_next(self, error_message: str = None):
        """Advance to the next token and ensure a non-spacing one appears before the document ends."""

        self._next_non_spacing_token()
        if self._token.type == TokenType.END_OF_DATA:
            self._unexpected_end(error_message if error_message else "Unexpected end")

    def _next_expecting_end_of_line_or_document(self):
        """Consume the next token, expecting the end of the line or end of the document."""

        self._next_non_spacing_token()
        if self._token.type not in (TokenType.LINE_BREAK, TokenType.END_OF_DATA):
            self._syntax_error("Expected the end of the line, or the end of the document.")
        if self._token.type != TokenType.END_OF_DATA:
            self._next_token()

    def _handle_value(self) -> Assignment:
        """Parse a value assignment starting at the current token."""

        if not isinstance(self._token.value, Name):
            self._internal_error("Unexpected value for name token")
        name: Name = self._token.value
        try:
            if name.is_meta():
                return self._handle_meta_value()
            assignment_location = self._location()
            if self._current_name_path is None:
                self._syntax_error("A value cannot be assigned outside a section.")
            self._expect_next("Unexpected end after name, expected a value separator")
            assert self._token.type == TokenType.NAME_VALUE_SEPARATOR
            self._expect_next("Unexpected end after value separator, expected a value on this or the next line")
            if self._token.type == TokenType.LINE_BREAK:
                self._expect_next("Unexpected end after the value separator and line-break, expected a value")
                assert self._token.type == TokenType.INDENTATION
                self._expect_next(
                    "Unexpected end after the value separator, line-break and indentation, expected a value"
                )
                if self._token.type == TokenType.MULTI_LINE_VALUE_LIST_SEPARATOR:
                    return self._handle_multi_line_value_list(name, assignment_location)
            if self._token.type.is_multi_line_open():
                return self._handle_multi_line_value(name, assignment_location)
            value = self._handle_single_value_or_value_list(name)
            return Assignment(AssignmentType.VALUE, self._current_name_path / name, assignment_location, value)
        except Error as e:
            if not e.name_path:  # Add the name to the error message.
                raise e.with_name_path(NamePath(name)) from e
            raise

    def _handle_single_value_or_value_list(self, name: Name) -> ValueImpl:
        """Parse a single value or a comma-separated list of values."""

        values: list[Tuple[ValueStorageType, Location]] = []
        assert self._token.type.is_single_line_value()
        list_location = self._location()
        values.append((self._token.value, self._location()))
        self._next_non_spacing_token()
        while True:
            if self._token.type in (TokenType.LINE_BREAK, TokenType.END_OF_DATA):
                if self._token.type == TokenType.LINE_BREAK:
                    self._next_token()  # Consume the line break
                break
            assert self._token.type == TokenType.VALUE_LIST_SEPARATOR
            self._expect_next("Unexpected end after value separator, expected a value")
            assert self._token.type.is_single_line_value()
            values.append((self._token.value, self._location()))
            self._next_non_spacing_token()
        if len(values) == 1:
            value_data, location = values[0]
            return ValueImpl.from_data(name, value_data, location)
        value = ValueImpl(ValueType.VALUE_LIST, name, location=list_location)
        for index, entry in enumerate(values):
            value_data, location = entry
            child_value = ValueImpl.from_data(Name(NameType.INDEX, index), value_data, location)
            value.add_child(child_value)
        return value

    def _handle_multi_line_value(self, name: Name, assignment_location: Location) -> Assignment:
        """Parse a multi-line value starting at the current token."""

        value_location = self._location()
        if self._token.type in (TokenType.MULTI_LINE_TEXT_OPEN, TokenType.MULTI_LINE_CODE_OPEN):
            text = self._handle_multi_line_text()
            value = ValueImpl(ValueType.TEXT, name, text, value_location)
        elif self._token.type == TokenType.MULTI_LINE_REGEX_OPEN:
            text = self._handle_multi_line_text()
            try:
                regex = re.compile(text)
                value = ValueImpl(ValueType.REGEX, name, regex, value_location)
            except re.error as e:
                raise ConfSyntaxError(
                    f"Invalid regular expression", source=assignment_location, system_message=str(e)
                ) from e
        else:
            assert self._token.type == TokenType.MULTI_LINE_BYTES_OPEN
            data = self._handle_multi_line_bytes()
            value = ValueImpl(ValueType.BYTES, name, bytes(data), value_location)
        return Assignment(AssignmentType.VALUE, self._current_name_path / name, assignment_location, value)

    def _handle_multi_line_text(self) -> str:
        """Parse the body of a multi-line text or code block."""

        text_parts: list[str] = []
        self._expect_next("Unexpected end after multi-line open quote")
        if self._token.type == TokenType.MULTI_LINE_CODE_LANGUAGE:  # Skip code language.
            self._expect_next("Unexpected end after multi-line code language, expected a value")
        assert self._token.type == TokenType.LINE_BREAK
        self._expect_next("Unexpected end in multi-line value")
        while True:
            if self._token.type == TokenType.LINE_BREAK:
                text_parts.append("\n")
                self._expect_next("Unexpected end in multi-line value")
                continue
            assert self._token.type == TokenType.INDENTATION
            self._expect_next("Unexpected end in multi-line value")
            if self._token.type.is_multi_line_close():
                self._next_expecting_end_of_line_or_document()
                break
            if self._token.type.is_multi_line_text():
                assert isinstance(self._token.value, str)
                text_parts.append(self._token.value)
                self._expect_next("Unexpected end in multi-line value")
            assert self._token.type == TokenType.LINE_BREAK
            self._expect_next("Unexpected end in multi-line value")
            text_parts.append("\n")
        if text_parts:  # Remove the last line-break from the text.
            text_parts.pop()
        return "".join(text_parts)

    def _handle_multi_line_bytes(self) -> bytearray:
        """Parse the body of a multi-line bytes literal."""

        data = bytearray()
        self._expect_next("Unexpected end after multi-line open quote")
        if self._token.type == TokenType.MULTI_LINE_BYTES_FORMAT:
            self._expect_next("Unexpected end after multi-line open quote")
        assert self._token.type == TokenType.LINE_BREAK
        self._expect_next("Unexpected end in multi-line bytes")
        while True:
            if self._token.type == TokenType.LINE_BREAK:
                self._expect_next("Unexpected end in multi-line bytes")
                continue
            assert self._token.type == TokenType.INDENTATION
            self._expect_next("Unexpected end in multi-line bytes")
            if self._token.type.is_multi_line_close():
                self._next_expecting_end_of_line_or_document()
                break
            if self._token.type == TokenType.MULTI_LINE_BYTES:
                assert isinstance(self._token.value, bytes)
                data.extend(self._token.value)
                self._expect_next("Unexpected end in multi-line bytes")
            assert self._token.type == TokenType.LINE_BREAK
            self._expect_next("Unexpected end in multi-line bytes")
        return data

    def _handle_multi_line_value_list(self, name: Name, assignment_location: Location):
        """Parse a multi-line list of values."""

        values: list[ValueImpl] = []
        assert self._token.type == TokenType.MULTI_LINE_VALUE_LIST_SEPARATOR
        list_location = self._location()
        sub_list_location = self._location()
        self._next_non_spacing_token()
        index = 0
        while True:
            value = self._handle_single_value_or_value_list(Name(NameType.INDEX, index))
            if value.type == ValueType.VALUE_LIST:
                value.location = sub_list_location
            values.append(value)
            if self._token.type != TokenType.INDENTATION:
                break  # End of the list
            self._expect_next("Unexpected end after indentation, expected another entry.")
            assert self._token.type == TokenType.MULTI_LINE_VALUE_LIST_SEPARATOR
            sub_list_location = self._location()
            self._expect_next("Unexpected end after multi-line value list separator, expected another entry.")
            index += 1
        if len(values) == 1:  # Lists with one element are handled like a single value.
            value = values[0]
            value.name = name
            return Assignment(AssignmentType.VALUE, self._current_name_path / name, assignment_location, value)
        value = ValueImpl(ValueType.VALUE_LIST, name, location=list_location)
        for index, child_value in enumerate(values):
            value.add_child(child_value)
        return Assignment(AssignmentType.VALUE, self._current_name_path / name, assignment_location, value)

    def _handle_meta_value(self) -> Assignment:
        """Parse a meta-value such as ``@version`` or ``@features``."""

        if not isinstance(self._token.value, Name):
            self._internal_error("Unexpected value for a name token")
        name: Name = self._token.value
        if name not in META_NAMES:
            self._unsupported("Unsupported meta value name")
        assignment_location = self._location()

        # signature location is checked in the lexer

        if name in (META_NAME_VERSION, META_NAME_FEATURES):
            if not self._in_document_root:
                self._syntax_error(
                    "The '@version' and '@features' meta-values must be defined before the first section."
                )

        if name == META_NAME_VERSION and self._read_meta_version:
            self._syntax_error("The '@version' meta-value must be defined only once.")
        if name == META_NAME_FEATURES and self._read_meta_features:
            self._syntax_error("The '@features' meta-value must be defined only once.")

        self._expect_next()
        if self._token.type is not TokenType.NAME_VALUE_SEPARATOR:
            self._syntax_error("Expected a value separator after the meta name")

        self._expect_next()
        if self._token.type is not TokenType.TEXT:
            self._syntax_error("Only single-line text is supported for a meta value or command.")
        text: str = self._token.value
        value_location = self._location()

        self._next_non_spacing_token()  # We may have reached the end of the document, which is fine at this point.
        if self._token.type == TokenType.VALUE_LIST_SEPARATOR:
            self._syntax_error("Only a text value is supported for a meta value or command.")
        assert self._token.type in (TokenType.LINE_BREAK, TokenType.END_OF_DATA)
        if self._token.type == TokenType.LINE_BREAK:
            self._next_token()  # Consume the line-break

        if name == META_NAME_VERSION:
            self._read_meta_version = True
            if text != "1.0":
                self._unsupported("This parser only supports version 1.0 of the configuration language.")
        elif name == META_NAME_FEATURES:
            self._read_meta_features = True
            self._verify_features(text)
        elif name == META_NAME_INCLUDE:
            self._current_absolute_name_path = None
            self._current_name_path = None

        value = ValueImpl(ValueType.TEXT, name, text, value_location)
        return Assignment(AssignmentType.META_VALUE, NamePath(name), assignment_location, value)

    def _handle_section(self) -> Assignment:
        """Parse a map or list section header. Most checks are handled by the lexer."""

        is_section_list = self._token.type == TokenType.SECTION_LIST_OPEN
        location = Location(self._source_identifier, self._token.begin)

        self._expect_next("Expected a section name")

        is_relative = False
        path = NamePath()
        if self._token.type == TokenType.NAME_PATH_SEPARATOR:
            is_relative = True
            self._expect_next("Expected a section name")

        while True:
            assert self._token.type == TokenType.NAME
            path.append(self._token.value)
            self._expect_next("Unexpected end in section name-path")
            if self._token.type in (TokenType.SECTION_MAP_CLOSE, TokenType.SECTION_LIST_CLOSE):
                break
            assert self._token.type == TokenType.NAME_PATH_SEPARATOR
            self._expect_next("Unexpected end in section name-path")

        self._next_expecting_end_of_line_or_document()
        if is_relative:
            if not self._current_absolute_name_path:
                self._syntax_error("There is no absolute section definition before this relative one.")
            path = self._current_absolute_name_path / path
        else:
            self._current_absolute_name_path = path.copy()

        self._current_name_path = path.copy()
        self._in_document_root = False

        if is_section_list:
            return Assignment(AssignmentType.SECTION_LIST, path, location, None)
        return Assignment(AssignmentType.SECTION_MAP, path, location, None)

    def _verify_features(self, text: str) -> None:
        """Ensure that all features listed in ``@features`` are supported."""

        features = [f.lower() for f in text.strip().split(sep=" ") if f]
        for feature in features:
            if feature not in SUPPORTED_FEATURES:
                self._unsupported(f"Feature '{feature}' is not supported by this parser.")
