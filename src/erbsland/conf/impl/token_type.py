#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import enum


class TokenType(enum.StrEnum):
    """Enumerates all lexical token categories."""

    END_OF_DATA = "EndOfData"  # The end of the data stream.
    ERROR = "Error"  # Marks erroneous syntax.
    LINE_BREAK = "LineBreak"  # A line break.
    SPACING = "Spacing"  # A block of spacing.
    INDENTATION = "Indentation"  # A block with indentation.
    COMMENT = "Comment"  # A comment.
    NAME = "Name"  # A regular name, meta-name or text-name (stored as ``Name``).
    NAME_VALUE_SEPARATOR = "NameValueSeparator"  # A value separator ``:``.
    VALUE_LIST_SEPARATOR = "ValueListSeparator"  # A value list separator ``,`.
    MULTI_LINE_VALUE_LIST_SEPARATOR = "MultiLineValueListSeparator"  # A multi-line value separator ``*``.
    NAME_PATH_SEPARATOR = "NamePathSeparator"  # A name path separator ``.``.
    INTEGER = "Integer"  # An integer literal.
    BOOLEAN = "Boolean"  # A boolean literal.
    FLOAT = "Float"  # A floating-point literal.
    TEXT = "Text"  # A single-line text.
    MULTI_LINE_TEXT_OPEN = "MultiLineTextOpen"  # The start of a multi-line text block.
    MULTI_LINE_TEXT_CLOSE = "MultiLineTextClose"  # The end of a multi-line text block.
    MULTI_LINE_TEXT = "MultiLineText"  # A line within a multi-line text.
    CODE = "Code"  # A single-line code block.
    MULTI_LINE_CODE_OPEN = "MultiLineCodeOpen"  # The start of a multi-line code block.
    MULTI_LINE_CODE_LANGUAGE = "MultiLineCodeLanguage"  # The language identifier of a multi-line code block.
    MULTI_LINE_CODE_CLOSE = "MultiLineCodeClose"  # The end of a multi-line code block.
    MULTI_LINE_CODE = "MultiLineCode"  # A line within a multi-line code block.
    REG_EX = "RegEx"  # A single-line regular expression.
    MULTI_LINE_REGEX_OPEN = "MultiLineRegexOpen"  # The start of a multi-line regular expression block.
    MULTI_LINE_REGEX_CLOSE = "MultiLineRegexClose"  # The end of a multi-line regular expression block.
    MULTI_LINE_REGEX = "MultiLineRegex"  # A line within a multi-line regular expression block.
    BYTES = "Bytes"  # A single-line block of bytes.
    MULTI_LINE_BYTES_OPEN = "MultiLineBytesOpen"  # The start of a multi-line bytes block.
    MULTI_LINE_BYTES_FORMAT = "MultiLineBytesFormat"  # The format of a multi-line bytes block.
    MULTI_LINE_BYTES_CLOSE = "MultiLineBytesClose"  # The end of a multi-line bytes block.
    MULTI_LINE_BYTES = "MultiLineBytes"  # A line within a multi-line bytes block.
    DATE = "Date"  # A date literal.
    TIME = "Time"  # A time literal.
    DATE_TIME = "DateTime"  # A date/time literal.
    TIME_DELTA = "TimeDelta"  # A time-delta literal.
    SECTION_MAP_OPEN = "SectionMapOpen"  # The start of a section map.
    SECTION_MAP_CLOSE = "SectionMapClose"  # The end of a section map.
    SECTION_LIST_OPEN = "SectionListOpen"  # The start of a section list block.
    SECTION_LIST_CLOSE = "SectionListClose"  # The end of a section list block.

    def is_multi_line_open(self) -> bool:
        """Return ``True`` if the token opens a multi-line block."""

        return self in (
            TokenType.MULTI_LINE_TEXT_OPEN,
            TokenType.MULTI_LINE_CODE_OPEN,
            TokenType.MULTI_LINE_REGEX_OPEN,
            TokenType.MULTI_LINE_BYTES_OPEN,
        )

    def is_multi_line_close(self) -> bool:
        """Return ``True`` if the token closes a multi-line block."""

        return self in (
            TokenType.MULTI_LINE_TEXT_CLOSE,
            TokenType.MULTI_LINE_CODE_CLOSE,
            TokenType.MULTI_LINE_REGEX_CLOSE,
            TokenType.MULTI_LINE_BYTES_CLOSE,
        )

    def is_multi_line_text(self) -> bool:
        """Return ``True`` if the token represents multi-line textual content."""

        return self in (TokenType.MULTI_LINE_TEXT, TokenType.MULTI_LINE_CODE, TokenType.MULTI_LINE_REGEX)

    def is_single_line_value(self) -> bool:
        """Return ``True`` if the token represents a single-line value literal."""

        return self in (
            TokenType.INTEGER,
            TokenType.BOOLEAN,
            TokenType.FLOAT,
            TokenType.TEXT,
            TokenType.CODE,
            TokenType.REG_EX,
            TokenType.BYTES,
            TokenType.DATE,
            TokenType.TIME,
            TokenType.DATE_TIME,
            TokenType.TIME_DELTA,
        )

    def is_spacing(self) -> bool:
        """Return ``True`` if the token represents spacing or comments."""

        return self in (TokenType.SPACING, TokenType.COMMENT, TokenType.ERROR)
