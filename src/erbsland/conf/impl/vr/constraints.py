# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Constraint compilation and scalar comparison primitives."""

from __future__ import annotations

import datetime as dt
import math
import re
import sys
import unicodedata
from typing import Any

from erbsland.conf.error import ConfValidationError
from erbsland.conf.name import Name
from erbsland.conf.impl.value_storage_type import value_type_from_storage_type
from erbsland.conf.vr.rule import Constraint
from erbsland.conf.vr.rule_type import RuleType, SECTION_TYPES, LIST_TYPES
from .model import Node, fail, freeze

CONSTRAINTS = frozenset(
    {"minimum", "maximum", "equals", "in", "multiple", "matches", "starts", "ends", "contains", "chars", "key"}
)
VERSIONS = frozenset({"version", "minimum_version", "maximum_version"})
ATTRIBUTES = frozenset({"title", "description", "error", "default", "is_optional", "is_secret", "case_sensitive"})
SIZE_TYPES = SECTION_TYPES | LIST_TYPES | {RuleType.TEXT, RuleType.BYTES}
FLOAT_TOLERANCE = 8 * sys.float_info.epsilon


def ordered(value: Any) -> Any:
    """
    Return a comparison key that preserves date-time nanoseconds and offsets.

    Date-times become integer nanoseconds relative to the ordinal-day origin;
    naive date-times are interpreted as UTC. Other values pass through unchanged.
    This keeps definition-bound checks and document comparisons consistent.
    """
    if not isinstance(value, dt.datetime):
        return value
    seconds = value.toordinal() * 86400 + value.hour * 3600 + value.minute * 60 + value.second
    result = seconds * 1_000_000_000 + getattr(value, "nanosecond", value.microsecond * 1000)
    offset = value.utcoffset()
    if offset is not None:
        result -= ((offset.days * 86400 + offset.seconds) * 1_000_000 + offset.microseconds) * 1000
    return result


def equal(a: Any, b: Any, case_sensitive: bool = False) -> bool:
    """
    Compare already type-checked operands using validation equality semantics.

    Text uses Unicode case folding unless case sensitivity is requested. Floats
    use ``FLOAT_TOLERANCE`` for both relative and absolute tolerance, with NaN
    equal to NaN. All other operands use their native equality operation.
    """
    if isinstance(a, str) and isinstance(b, str) and not case_sensitive:
        return a.casefold() == b.casefold()
    if type(a) is float and type(b) is float:
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return math.isclose(a, b, rel_tol=FLOAT_TOLERANCE, abs_tol=FLOAT_TOLERANCE)
    return a == b


def scalar_matches(type_: RuleType, value: Any) -> bool:
    """Check a native scalar's storage type without coercion, keeping booleans distinct from integers."""
    try:
        return type_.matches(value_type_from_storage_type(type(value)))
    except ValueError:
        return False


def sequence(value: Any) -> tuple[Any, ...]:
    """Treat a frozen scalar as a one-item tuple, preserving an existing tuple."""
    return value if isinstance(value, tuple) else (value,)


def compile_chars(value: Any) -> tuple[tuple[int, int], ...]:
    """
    Compile named character sets, explicit sets and ranges into code-point intervals.

    :param value: One character-set expression or a frozen tuple of expressions.
    :returns: Inclusive intervals used for case-sensitive character membership.
    :raises ConfValidationError: If an expression is empty, unknown or malformed.
    """
    result = []
    named = {
        "letters": ((65, 90), (97, 122)),
        "digits": ((48, 57),),
        "control": ((1, 31), (127, 160)),
        "linebreak": ((10, 10), (13, 13)),
        "spacing": ((9, 9), (32, 32)),
    }
    for part in sequence(value):
        if not isinstance(part, str) or not part:
            raise ConfValidationError("'chars' requires nonempty character-set definitions")
        if part.startswith("("):
            if (
                len(part) != 5
                or part[2] != "-"
                or part[-1] != ")"
                or part[1] >= part[3]
                or any(unicodedata.category(c).startswith("M") for c in (part[1], part[3]))
            ):
                raise ConfValidationError("Invalid character range in 'chars'")
            result.append((ord(part[1]), ord(part[3])))
        elif part.startswith("["):
            if not part.endswith("]") or len(part) < 3 or len(set(part[1:-1])) != len(part[1:-1]):
                raise ConfValidationError("Invalid or duplicate characters in 'chars'")
            result.extend((ord(c), ord(c)) for c in part[1:-1])
        else:
            key = part.lower().replace(" ", "_")
            if key not in named:
                raise ConfValidationError("Unknown named character set")
            result.extend(named[key])
    return tuple(result)


def validate_operand(kind: str, value: Any, type_: RuleType, sensitive: bool) -> Any:
    """
    Check a constraint's applicability and normalize its frozen operand.

    Numeric types must match exactly. Collection dimensions, membership
    duplicates and special floating-point values are checked before evaluation.
    Regex operands are compiled here; character sets are checked here and
    prepared separately by ``compile_options``.

    :param kind: Constraint identifier with any ``not_`` prefix removed.
    :param value: Operand normalized by ``freeze``.
    :param type_: The rule's effective type.
    :param sensitive: Whether text membership comparisons are case-sensitive.
    :returns: The checked scalar, tuple or compiled regular expression.
    :raises ConfValidationError: If the operand or rule type is unsupported.
    """
    if kind in {"minimum", "maximum", "multiple", "equals"}:
        if type_ == RuleType.VALUE_MATRIX:
            if not isinstance(value, tuple):
                raise ConfValidationError("Matrix constraints require two integers")
            if len(value) != 2 or any(type(v) is not int or kind != "multiple" and v < 0 for v in value):
                raise ConfValidationError("Matrix constraints require two integers; dimensions cannot be negative")
            if kind == "multiple" and any(v == 0 for v in value):
                raise ConfValidationError("'multiple' requires nonzero divisors")
            return value
        if type_ in SIZE_TYPES:
            if kind == "equals" and type_ in (RuleType.TEXT, RuleType.BYTES) and scalar_matches(type_, value):
                return value
            if type(value) is not int or kind != "multiple" and value < 0:
                raise ConfValidationError("Size constraints require integers; sizes cannot be negative")
        elif type_ in (RuleType.INTEGER, RuleType.FLOAT):
            if not scalar_matches(type_, value):
                raise ConfValidationError("Numeric constraint type must match the rule")
            if kind != "equals" and isinstance(value, float) and math.isnan(value):
                raise ConfValidationError("NaN is not a valid constraint operand")
        elif kind == "equals" and type_ == RuleType.BOOLEAN:
            if type(value) is not bool:
                raise ConfValidationError("Boolean equality requires a boolean")
        elif kind in ("minimum", "maximum") and type_ in (RuleType.DATE, RuleType.DATE_TIME):
            if not scalar_matches(type_, value):
                raise ConfValidationError("Date constraint type must match the rule")
        else:
            raise ConfValidationError(f"'{kind}' does not support {type_.value}")
        if kind == "multiple" and (value == 0 or isinstance(value, float) and not math.isfinite(value)):
            raise ConfValidationError("'multiple' requires a finite nonzero divisor")
    elif kind == "in":
        if type_ not in (RuleType.INTEGER, RuleType.FLOAT, RuleType.TEXT, RuleType.BYTES):
            raise ConfValidationError("'in' requires an integer, float, text or bytes rule")
        values = sequence(value)
        if not values or any(not scalar_matches(type_, v) for v in values):
            raise ConfValidationError("'in' values must match the rule type")
        if any(equal(v, other, sensitive) for i, v in enumerate(values) for other in values[:i]):
            raise ConfValidationError("Duplicate values in 'in' constraint")
        if any(isinstance(v, float) and math.isnan(v) for v in values):
            raise ConfValidationError("NaN is not a valid membership operand")
        return values
    elif kind in ("starts", "ends", "contains"):
        if type_ != RuleType.TEXT or not sequence(value) or any(type(v) is not str for v in sequence(value)):
            raise ConfValidationError(f"'{kind}' requires text operands on a text rule")
        return sequence(value)
    elif kind == "chars":
        if type_ != RuleType.TEXT:
            raise ConfValidationError("'chars' requires a text rule")
        compile_chars(value)
        return sequence(value)
    elif kind == "matches":
        if type_ != RuleType.TEXT:
            raise ConfValidationError("'matches' requires a text rule")
        try:
            pattern = re.compile(value)
        except (re.error, TypeError):
            raise ConfValidationError("Invalid regular expression in 'matches'") from None
        if not isinstance(pattern.pattern, str) or not pattern.pattern:
            raise ConfValidationError("'matches' requires a nonempty text regular expression")
        return pattern
    elif kind == "key":
        if type_ not in (RuleType.TEXT, RuleType.INTEGER):
            raise ConfValidationError("'key' requires a text or integer rule")
        if not sequence(value) or any(type(v) is not str for v in sequence(value)):
            raise ConfValidationError("'key' requires index names")
        return sequence(value)
    return value


def compile_options(node: Node, path: tuple[Name, ...]) -> tuple[tuple[Constraint, ...], tuple[tuple[str, Any], ...]]:
    """
    Check attributes and compile constraints in their declaration order.

    Version restrictions are kept separate because they select definitions
    rather than validate values. Custom errors are attached to their matching
    constraints, and positive/negative conflicts and inconsistent bounds are
    rejected before any document is validated.

    :param node: Definition containing ordered options and source locations.
    :param path: Declaration path to use for definition errors.
    :returns: Value constraints and version restrictions, each in definition order.
    :raises ConfValidationError: If an option is invalid, located at its definition.
    """
    constraints = []
    versions = []
    seen = set()
    sensitive = node.options.get("case_sensitive", False)
    for name, raw in node.options.items():
        value = freeze(raw)
        kind = name.removeprefix("not_")
        if name in ATTRIBUTES:
            if name in ("title", "description", "error") and type(value) is not str:
                fail(f"'{name}' must be text", node, path, name)
            if name in ("is_optional", "is_secret", "case_sensitive") and type(value) is not bool:
                fail(f"'{name}' must be boolean", node, path, name)
            continue
        if name.endswith("_error"):
            target = name.removesuffix("_error")
            if target not in node.options or target.removeprefix("not_") not in CONSTRAINTS:
                fail("Custom error has no corresponding constraint", node, path, name)
            if type(value) is not str:
                fail("Custom error must be text", node, path, name)
            continue
        if kind not in CONSTRAINTS | VERSIONS:
            fail(f"Unknown rule attribute or constraint '{name}'", node, path, name)
        if kind in seen:
            fail("Positive and negative constraints cannot be combined", node, path, name)
        seen.add(kind)
        try:
            if kind in VERSIONS:
                numbers = sequence(value) if kind == "version" else (value,)
                if (
                    not numbers
                    or any(type(v) is not int or v < 0 for v in numbers)
                    or len(set(numbers)) != len(numbers)
                ):
                    raise ConfValidationError("Versions must be unique nonnegative integers")
                versions.append((name, numbers if kind == "version" else value))
            else:
                value = validate_operand(kind, value, node.type, sensitive)
                prepared = None
                if kind == "chars":
                    prepared = compile_chars(value)
                elif kind == "key":
                    from .relationships import key_reference

                    prepared = tuple(key_reference(text) for text in value)
                constraints.append(
                    Constraint(
                        name, value, node.options.get(name + "_error", ""), node.option_locations.get(name), prepared
                    )
                )
        except ConfValidationError as error:
            fail(error.message, node, path, name)
    minimum = node.options.get("minimum")
    maximum = node.options.get("maximum")
    if minimum is not None and maximum is not None:
        if node.type == RuleType.VALUE_MATRIX:
            minimum = next(c.value for c in constraints if c.name == "minimum")
            maximum = next(c.value for c in constraints if c.name == "maximum")
        try:
            invalid = (
                any(a > b for a, b in zip(minimum, maximum))
                if isinstance(minimum, tuple)
                else ordered(minimum) > ordered(maximum)
            )
        except TypeError:
            fail("Incompatible minimum and maximum bounds", node, path)
        if invalid:
            fail("The minimum must not exceed the maximum", node, path)
    return tuple(constraints), tuple(versions)
