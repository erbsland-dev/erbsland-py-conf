# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Types accepted by validation rules."""

from __future__ import annotations

import datetime as dt
import re
from enum import StrEnum
from typing import Any, Type

from erbsland.conf.datetime import DateTime, Time
from erbsland.conf.error import ConfValidationError
from erbsland.conf.time_delta import TimeDelta
from erbsland.conf.value_type import ValueType


class RuleType(StrEnum):
    """ELCL validation types, including collection and unrestricted types."""

    INTEGER = "Integer"
    BOOLEAN = "Boolean"
    FLOAT = "Float"
    TEXT = "Text"
    DATE = "Date"
    TIME = "Time"
    DATE_TIME = "DateTime"
    BYTES = "Bytes"
    TIME_DELTA = "TimeDelta"
    REGEX = "RegEx"
    VALUE = "Value"
    VALUE_LIST = "ValueList"
    VALUE_MATRIX = "ValueMatrix"
    SECTION = "Section"
    SECTION_LIST = "SectionList"
    SECTION_WITH_TEXTS = "SectionWithTexts"
    NOT_VALIDATED = "NotValidated"
    ALTERNATIVES = "Alternatives"

    @classmethod
    def from_type(cls, value: RuleType | Type[Any] | str) -> RuleType:
        """Resolve a native scalar type, enum, or ELCL type identifier."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.lower().replace(" ", "_")
            for member in cls:
                if normalized in (member.value.lower(), member.name.lower()):
                    return member
        elif isinstance(value, type):
            native_types = {
                int: cls.INTEGER,
                bool: cls.BOOLEAN,
                float: cls.FLOAT,
                str: cls.TEXT,
                bytes: cls.BYTES,
                dt.date: cls.DATE,
                dt.time: cls.TIME,
                Time: cls.TIME,
                dt.datetime: cls.DATE_TIME,
                DateTime: cls.DATE_TIME,
                dt.timedelta: cls.TIME_DELTA,
                TimeDelta: cls.TIME_DELTA,
                re.Pattern: cls.REGEX,
            }
            if value in native_types:
                return native_types[value]
        raise ConfValidationError("Unknown validation rule type")

    def is_scalar(self) -> bool:
        """Return whether this rule accepts scalar values."""
        return self in SCALAR_TYPES

    def matches(self, value_type: ValueType) -> bool:
        """Test the stored type without converting the value."""
        if self == self.NOT_VALIDATED:
            return True
        if self == self.VALUE:
            return value_type.is_single_value()
        if self in (self.VALUE_LIST, self.VALUE_MATRIX):
            return value_type == ValueType.VALUE_LIST or value_type.is_single_value()
        if self == self.SECTION:
            return value_type in (ValueType.SECTION_WITH_NAMES, ValueType.INTERMEDIATE_SECTION, ValueType.DOCUMENT)
        return self.value == value_type.value


SCALAR_TYPES = frozenset(
    {
        RuleType.INTEGER,
        RuleType.BOOLEAN,
        RuleType.FLOAT,
        RuleType.TEXT,
        RuleType.DATE,
        RuleType.TIME,
        RuleType.DATE_TIME,
        RuleType.BYTES,
        RuleType.TIME_DELTA,
        RuleType.REGEX,
        RuleType.VALUE,
    }
)
LIST_TYPES = frozenset({RuleType.VALUE_LIST, RuleType.VALUE_MATRIX, RuleType.SECTION_LIST})
SECTION_TYPES = frozenset({RuleType.SECTION, RuleType.SECTION_WITH_TEXTS})
TypeLike = RuleType | Type[Any] | str
