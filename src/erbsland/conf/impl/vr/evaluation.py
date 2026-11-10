# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Evaluate already checked constraints without modifying values."""

from __future__ import annotations

import math
from typing import Any

from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType
from erbsland.conf.vr.rule import Rule, Constraint
from erbsland.conf.vr.rule_type import RuleType
from .constraints import equal, ordered, FLOAT_TOLERANCE


def elements(value: Value) -> tuple[Value, ...]:
    """Return list entries or a one-item scalar view without changing the stored value."""
    return tuple(value) if value.type == ValueType.VALUE_LIST else (value,)


def dimensions(value: Value) -> tuple[int, int]:
    """Return the matrix's row count and greatest row width, treating scalar rows as width one."""
    rows = elements(value)
    return len(rows), max((len(elements(row)) for row in rows), default=0)


def quantity(value: Value, rule: Rule, constraint: Constraint) -> Any:
    """
    Select the scalar value or size to which a numeric constraint applies.

    Lists use their entry count, matrices use dimensions and sections use their
    child count. Text and bytes use their length only for integer operands;
    equality with a text or bytes operand compares the contents.
    """
    if rule.type == RuleType.VALUE_MATRIX:
        return dimensions(value)
    if rule.type == RuleType.VALUE_LIST:
        return len(elements(value))
    if value.type.is_container():
        return len(value)
    if value.type in (ValueType.TEXT, ValueType.BYTES) and type(constraint.value) is int:
        return len(value.native)
    return value.native


def multiple(value: int | float, divisor: int | float) -> bool:
    """
    Test divisibility using exact integer arithmetic or tolerant float quotients.

    The divisor must already be checked as finite and nonzero. Nonfinite values
    or quotients fail; finite float quotients use ``FLOAT_TOLERANCE`` when
    compared with the nearest integer.
    """
    if type(value) is int and type(divisor) is int:
        return value % divisor == 0
    if not math.isfinite(value):
        return False
    quotient = value / divisor
    if not math.isfinite(quotient):
        return False
    return math.isclose(quotient, round(quotient), rel_tol=FLOAT_TOLERANCE, abs_tol=FLOAT_TOLERANCE)


def compare(kind: str, actual: Any, expected: Any, sensitive: bool) -> bool:
    """
    Evaluate a positive minimum, maximum, equality or multiple comparison.

    Operands must already be type-compatible. Text equality uses ``sensitive``;
    date-time bounds use the same normalized instants as definition checking.
    Negation is applied by the caller.
    """
    if kind == "equals":
        return equal(actual, expected, sensitive)
    if kind == "multiple":
        return multiple(actual, expected)
    actual, expected = ordered(actual), ordered(expected)
    return actual >= expected if kind == "minimum" else actual <= expected


def passes(value: Value, rule: Rule, constraint: Constraint) -> bool:
    """
    Evaluate one compiled local constraint against a type-checked value.

    Most negated constraints invert the positive predicate. Matrix constraints
    instead negate each dimension check, and ``not_chars`` forbids any matching
    character. NaN fails both positive and negative bounds.

    :returns: Whether the constraint passes, without changing the value.
    :raises AssertionError: If a nonlocal or unknown constraint reaches this evaluator.
    """
    kind, expected = constraint.kind, constraint.value
    actual = value.native
    if kind in ("minimum", "maximum", "equals", "multiple"):
        actual = quantity(value, rule, constraint)
        if kind in ("minimum", "maximum") and isinstance(actual, float) and math.isnan(actual):
            return False
        if rule.type == RuleType.VALUE_MATRIX:
            comparisons = [(len(elements(value)), expected[0])]
            comparisons.extend((len(elements(row)), expected[1]) for row in elements(value))
            return all(compare(kind, a, b, rule.case_sensitive) != constraint.is_negated for a, b in comparisons)
        else:
            result = compare(kind, actual, expected, rule.case_sensitive)
    elif kind == "in":
        result = any(equal(actual, candidate, rule.case_sensitive) for candidate in expected)
    elif kind in ("starts", "ends", "contains"):
        if not rule.case_sensitive:
            actual = actual.casefold()
            expected = tuple(part.casefold() for part in expected)
        if kind == "starts":
            result = any(actual.startswith(part) for part in expected)
        elif kind == "ends":
            result = any(actual.endswith(part) for part in expected)
        else:
            result = any(part in actual for part in expected)
    elif kind == "matches":
        result = expected.search(actual) is not None
    elif kind == "chars":
        ranges = constraint._prepared
        contains = [any(low <= ord(c) <= high for low, high in ranges) for c in actual]
        # not_chars forbids every occurrence, rather than negating the entire string match.
        return not any(contains) if constraint.is_negated else all(contains)
    else:
        raise AssertionError(f"Unexpected compiled constraint: {kind}")
    return not result if constraint.is_negated else result
