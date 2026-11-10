# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Keyword types for Python rule declarations."""

from __future__ import annotations

import datetime as dt
import re
from typing import TypedDict

from erbsland.conf.time_delta import TimeDelta
from .rule_type import TypeLike

Scalar = int | bool | float | str | bytes | dt.date | dt.time | dt.datetime | dt.timedelta | TimeDelta | re.Pattern[str]
DefaultValue = Scalar | list[Scalar] | list[list[Scalar]] | tuple[Scalar, ...] | tuple[tuple[Scalar, ...], ...]
Bound = int | float | dt.date | tuple[int, int] | list[int]
Choices = Scalar | list[Scalar] | tuple[Scalar, ...]
Texts = str | list[str] | tuple[str, ...]


class RuleOptions(TypedDict, total=False):
    """ELCL attributes as Python keywords, in evaluation order."""

    title: str
    description: str
    error: str
    default: DefaultValue
    is_optional: bool
    is_secret: bool
    case_sensitive: bool
    minimum: Bound
    maximum: Bound
    equals: Choices
    multiple: int | float | tuple[int, int] | list[int]
    in_: Choices
    chars: Texts
    starts: Texts
    ends: Texts
    contains: Texts
    matches: str | re.Pattern[str]
    key: Texts
    version: int | list[int] | tuple[int, ...]
    minimum_version: int
    maximum_version: int
    not_minimum: Bound
    not_maximum: Bound
    not_equals: Choices
    not_multiple: int | float | tuple[int, int] | list[int]
    not_in: Choices
    not_chars: Texts
    not_starts: Texts
    not_ends: Texts
    not_contains: Texts
    not_matches: str | re.Pattern[str]
    not_key: Texts
    not_version: int | list[int] | tuple[int, ...]
    not_minimum_version: int
    not_maximum_version: int
    minimum_error: str
    maximum_error: str
    equals_error: str
    multiple_error: str
    in_error: str
    chars_error: str
    starts_error: str
    ends_error: str
    contains_error: str
    matches_error: str
    key_error: str
    not_minimum_error: str
    not_maximum_error: str
    not_equals_error: str
    not_multiple_error: str
    not_in_error: str
    not_chars_error: str
    not_starts_error: str
    not_ends_error: str
    not_contains_error: str
    not_matches_error: str
    not_key_error: str
    entry_type: TypeLike
    entry_options: RuleOptions
