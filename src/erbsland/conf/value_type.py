#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import enum


class ValueType(enum.StrEnum):
    """All possible types of configuration values."""

    UNDEFINED = "Undefined"
    """An undefined value type."""
    INTEGER = "Integer"
    """An integer value."""
    BOOLEAN = "Boolean"
    """A boolean value."""
    FLOAT = "Float"
    """A floating-point value."""
    TEXT = "Text"
    """A text value."""
    DATE = "Date"
    """A date value."""
    TIME = "Time"
    """A time value."""
    DATE_TIME = "DateTime"
    """A date-time value."""
    BYTES = "Bytes"
    """A bytes value."""
    TIME_DELTA = "TimeDelta"
    """A time-delta value."""
    REGEX = "RegEx"
    """A regular expression value."""
    VALUE_LIST = "ValueList"
    """A list of values."""
    SECTION_LIST = "SectionList"
    """A list of sections."""
    INTERMEDIATE_SECTION = "IntermediateSection"
    """An intermediate section."""
    SECTION_WITH_NAMES = "SectionWithNames"
    """A section containing named values."""
    SECTION_WITH_TEXTS = "SectionWithTexts"
    """A section containing text values."""
    DOCUMENT = "Document"
    """The root document value."""

    def is_single_value(self) -> bool:
        """Return ``True`` if this type represents a single scalar value."""
        return self in (
            ValueType.INTEGER,
            ValueType.BOOLEAN,
            ValueType.FLOAT,
            ValueType.TEXT,
            ValueType.DATE,
            ValueType.TIME,
            ValueType.DATE_TIME,
            ValueType.BYTES,
            ValueType.TIME_DELTA,
            ValueType.REGEX,
        )

    def is_list(self) -> bool:
        """Return ``True`` if this type represents a list."""
        return self in (
            ValueType.VALUE_LIST,
            ValueType.SECTION_LIST,
        )

    def is_map(self) -> bool:
        """Return ``True`` if this type represents a mapping."""
        return self in (
            ValueType.INTERMEDIATE_SECTION,
            ValueType.SECTION_WITH_NAMES,
            ValueType.SECTION_WITH_TEXTS,
            ValueType.DOCUMENT,
        )

    def is_container(self) -> bool:
        """Return ``True`` if this type can contain other values."""
        return self in (
            ValueType.VALUE_LIST,
            ValueType.SECTION_LIST,
            ValueType.INTERMEDIATE_SECTION,
            ValueType.SECTION_WITH_NAMES,
            ValueType.SECTION_WITH_TEXTS,
            ValueType.DOCUMENT,
        )

    def is_section(self) -> bool:
        """Return ``True`` if this type represents a section or a section list."""
        return self in (
            ValueType.INTERMEDIATE_SECTION,
            ValueType.SECTION_WITH_NAMES,
            ValueType.SECTION_WITH_TEXTS,
            ValueType.DOCUMENT,
            ValueType.SECTION_LIST,
        )
