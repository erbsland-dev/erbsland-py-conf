# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Immutable metadata for compiled validation rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from .rule_type import RuleType


@dataclass(frozen=True)
class Constraint:
    """A compiled constraint, in declaration order; sequences are immutable tuples."""

    name: str
    _value: Any = field(repr=False)
    error: str = ""
    location: Location | None = field(default=None, compare=False)
    _prepared: Any = field(default=None, compare=False, repr=False)

    @property
    def value(self) -> Any:
        """The immutable operand, with independent copies of date/time wrappers."""
        from erbsland.conf.impl.vr.model import freeze

        return freeze(self._value)

    @property
    def is_negated(self) -> bool:
        """Whether this is the negative form of the constraint."""
        return self.name.startswith("not_")

    @property
    def kind(self) -> str:
        """The constraint identifier without the negation prefix."""
        return self.name.removeprefix("not_")


@dataclass(frozen=True, slots=True, eq=False)
class Rule:
    """Read-only rule metadata. Name paths are returned as independent copies."""

    type: RuleType
    _path: tuple[Name, ...] = field(repr=False)
    _definition_path: tuple[Name, ...] = field(repr=False)
    _role: str = field(repr=False)
    _name: Name | None = field(repr=False)
    title: str = ""
    description: str = ""
    is_optional: bool = False
    is_secret: bool = False
    case_sensitive: bool = False
    custom_error: str = ""
    has_default: bool = False
    _default: Any = field(default=None, repr=False)
    constraints: tuple[Constraint, ...] = ()
    children: tuple[Rule, ...] = ()
    location: Location | None = None
    _versions: tuple[tuple[str, Any], ...] = field(default=(), repr=False)
    _keys: tuple[Any, ...] = field(default=(), repr=False)
    _dependencies: tuple[Any, ...] = field(default=(), repr=False)

    @property
    def name_path(self) -> NamePath:
        """Symbolic configuration path, with declaration escapes decoded."""
        return NamePath(list(self._path))

    @property
    def has_custom_error(self) -> bool:
        """Whether a nonempty node-level error message was provided."""
        return bool(self.custom_error)

    @property
    def default(self) -> Any:
        """The default payload, or None if absent; sequences are immutable tuples."""
        from erbsland.conf.impl.vr.model import freeze

        return freeze(self._default)

    @property
    def version_constraints(self) -> Mapping[str, int | tuple[int, ...]]:
        """Read-only version restrictions, separate from value constraints."""
        return MappingProxyType(dict(self._versions))

    def _active(self, version: int) -> bool:
        for name, expected in self._versions:
            kind = name.removeprefix("not_")
            if kind == "version":
                matched = version in expected
            elif kind == "minimum_version":
                matched = version >= expected
            else:
                matched = version <= expected
            if matched == name.startswith("not_"):
                return False
        if self.type == RuleType.ALTERNATIVES:
            return any(child._active(version) for child in self.children)
        return True

    def _child(self, role: str, name: Name | None = None) -> Rule | None:
        return next(
            (child for child in self.children if child._role == role and (name is None or child._name == name)), None
        )
