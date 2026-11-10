# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Mutable definitions shared by the document loader and Python builder."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from erbsland.conf.error import Error, ConfValidationError
from erbsland.conf.datetime import DateTime, Time
from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.time_delta import TimeDelta, TimeUnit
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType
from erbsland.conf.vr.rule_type import RuleType

PathLike = str | Name | NamePath


def path_parts(path: PathLike, *, indexes: bool = False) -> tuple[Name, ...]:
    """
    Normalize a literal configuration path into immutable name components.

    This helper does not decode ELCL declaration escapes. Meta names and text
    names are rejected; index components are accepted only when requested.

    :param indexes: Allow indexes, as required for composite-key references.
    :raises ConfValidationError: If the path is empty or contains unsupported components.
    """
    try:
        if isinstance(path, str):
            result = tuple(NamePath.from_text(path))
        elif isinstance(path, Name):
            result = (path,)
        elif isinstance(path, NamePath):
            result = tuple(path)
        else:
            raise ConfValidationError("Expected a string, Name or NamePath")
        if not result or any(not (p.is_regular() and not p.is_meta() or indexes and p.is_index()) for p in result):
            raise ConfValidationError("Expected a nonempty path containing regular names")
        return result
    except Error as error:
        raise ConfValidationError(error.message) from None


def regular_name(text: str) -> Name:
    """Normalize one regular, non-meta name, raising ConfValidationError for invalid input."""
    try:
        name = Name.create_regular(text)
        if name.is_meta():
            raise ConfValidationError("Meta names are not allowed in rules")
        return name
    except (Error, TypeError, ValueError):
        raise ConfValidationError("Invalid regular name in validation rules") from None


def freeze(value: Any) -> Any:
    """
    Detach supported mutable payloads before storing or exposing rule metadata.

    Lists and tuples become recursively copied tuples. Native time deltas become
    ELCL time deltas, and the library's time/date-time wrappers are copied without
    losing nanoseconds. Other values pass through unchanged; this helper does
    not check whether an operand is valid for a particular constraint.
    """
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, dt.timedelta):
        return TimeDelta((value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds, TimeUnit.MICROSECOND)
    if isinstance(value, DateTime):
        return DateTime(
            value.year,
            value.month,
            value.day,
            hour=value.hour,
            minute=value.minute,
            second=value.second,
            nanosecond=value.nanosecond,
            tzinfo=value.tzinfo,
            fold=value.fold,
        )
    if isinstance(value, Time):
        return Time(
            value.hour,
            value.minute,
            second=value.second,
            nanosecond=value.nanosecond,
            tzinfo=value.tzinfo,
            fold=value.fold,
        )
    return value


def native(value: Value) -> Any:
    """
    Extract a scalar payload or tuple of payloads from a parsed rule attribute.

    Scalar payloads are returned directly; snapshot compilation uses ``freeze``
    when an independent copy is required.

    :raises ConfValidationError: If the attribute contains a section or other non-value node.
    """
    if value.type == ValueType.VALUE_LIST:
        return tuple(native(child) for child in value)
    if not value.type.is_single_value():
        raise ConfValidationError("Expected a scalar or value list", source=value.location, name_path=value.name_path)
    return value.native


@dataclass
class Node:
    """
    A mutable definition shared by the ELCL loader and Python builder.

    Declaration spelling, decoded name and structural role are kept separate.
    This allows literal control-like names alongside structural definitions and
    preserves useful diagnostics after template expansion.

    :var name: Decoded target name, or None for the root.
    :var role: Root, named, entry, wildcard, name-constraint or alternative role.
    :var type: Effective rule type, possibly unset until a template child is merged.
    :var spelling: Original declaration component used in definition paths.
    :var options: Attributes and constraints in declaration order.
    :var children: Child definitions in declaration order.
    :var keys: Uncompiled scoped index records.
    :var dependencies: Uncompiled dependency records.
    :var location: Source location of the definition, when loaded from ELCL.
    :var option_locations: Per-option source locations retained through overrides.
    """

    name: Name | None = None
    role: str = "named"
    type: RuleType | None = None
    spelling: Name | None = None
    options: dict[str, Any] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    keys: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    location: Location | None = None
    option_locations: dict[str, Location | None] = field(default_factory=dict)

    def child(self, role: str, name: Name | None = None) -> Node | None:
        """Return the first child with the given role and optional literal target name."""
        return next(
            (child for child in self.children if child.role == role and (name is None or child.name == name)), None
        )

    def __deepcopy__(self, memo: dict) -> Node:
        """
        Copy a definition tree while preserving nanoseconds in native payloads.

        The standard datetime copying protocol cannot reconstruct the library's
        wrappers. Copying options through ``freeze`` also detaches valid sequence
        operands so later builder edits cannot affect a compiled snapshot.
        """
        # Python datetime subclasses cannot use datetime's pickle-based copying.
        from copy import deepcopy

        result = Node(
            name=self.name,
            role=self.role,
            type=self.type,
            spelling=self.spelling,
            options={k: freeze(v) for k, v in self.options.items()},
            children=[deepcopy(c, memo) for c in self.children],
            keys=deepcopy(self.keys, memo),
            dependencies=deepcopy(self.dependencies, memo),
            location=self.location,
            option_locations=dict(self.option_locations),
        )
        memo[id(self)] = result
        return result


def fail(message: str, node: Node, path: tuple[Name, ...], option: str | None = None) -> None:
    """
    Raise a definition error with the appropriate declaration path and source.

    :param path: Definition path at the insertion point, including any template use.
    :param option: Attribute to append to the path and use for a more precise location.
    :raises ConfValidationError: Always, using the option's location when available.
    """
    location = node.location
    if option is not None:
        location = node.option_locations.get(option, location)
        path = (*path, Name.create_regular(option))
    raise ConfValidationError(message, source=location, name_path=NamePath(list(path)))
