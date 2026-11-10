# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

import math
import re
import sys

import pytest

from erbsland.conf import ConfValidationError, DocumentBuilder, loads
from erbsland.conf.vr import RulesBuilder, RuleType


def validate_scalar(type_, value, **constraints):
    builder = RulesBuilder()
    builder.add_rule("value", type_, **constraints)
    document_builder = DocumentBuilder()
    document_builder.add_section_map("app")
    document_builder.add_value("app.value", value)
    document = document_builder.get_document_and_reset()
    builder.build().validate(document["app"], 1)


@pytest.mark.parametrize("constraint", ["equals", "in_"])
def test_float_comparison_tolerance(constraint):
    validate_scalar(float, 1.0 + 4 * sys.float_info.epsilon, **{constraint: 1.0})
    with pytest.raises(ConfValidationError):
        validate_scalar(float, 1.0 + 16 * sys.float_info.epsilon, **{constraint: 1.0})


@pytest.mark.parametrize("value", [0.9, -0.9, 0.0, 0.3, 1.0 + 4 * sys.float_info.epsilon])
def test_float_multiple_accepts_rounding_error(value):
    validate_scalar(float, value, multiple=0.1)


@pytest.mark.parametrize("value", [0.91, float("nan"), float("inf"), float("-inf")])
def test_float_multiple_rejects_nonmultiples_and_nonfinite_values(value):
    with pytest.raises(ConfValidationError):
        validate_scalar(float, value, multiple=0.1)


@pytest.mark.parametrize("divisor", [0.0, float("nan"), float("inf"), float("-inf")])
def test_float_multiple_rejects_invalid_divisors(divisor):
    with pytest.raises(ConfValidationError):
        validate_scalar(float, 1.0, multiple=divisor)


def test_nan_and_infinity_constraints():
    validate_scalar(float, math.nan, equals=math.nan)
    validate_scalar(float, math.inf, equals=math.inf)
    validate_scalar(float, math.inf, minimum=0.0)
    for constraint in ("minimum", "maximum", "not_minimum", "not_maximum"):
        with pytest.raises(ConfValidationError):
            validate_scalar(float, math.nan, **{constraint: 0.0})
    with pytest.raises(ConfValidationError):
        validate_scalar(float, 1.0, in_=[math.nan])


@pytest.mark.parametrize("type_, value", [(int, -6), (float, -6.0), (str, "abcdef"), (bytes, b"abcdef")])
def test_negative_multiple_divisors(type_, value):
    validate_scalar(type_, value, multiple=-2.0 if type_ is float else -2)


def test_negative_matrix_multiple_divisors():
    builder = RulesBuilder()
    matrix = builder.add_rule("matrix", RuleType.VALUE_MATRIX, multiple=(-2, -2))
    matrix.add_entry(int)
    rules = builder.build()
    rules.validate(loads("[app]\nmatrix:\n    * 1, 2\n    * 3, 4\n")["app"], 1)


def test_unicode_folding_is_independent_of_regex_and_character_sets():
    validate_scalar(str, "Straße", equals="STRASSE", in_=["strasse"], starts="stras", ends="SSE", contains="SS")
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "Straße", equals="STRASSE", case_sensitive=True)
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "A", chars="(a-z)")
    validate_scalar(str, "Σ", equals="ς")
    validate_scalar(str, "é", minimum=1, maximum=1)
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "e\u0301", maximum=1)
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "ABC", matches="abc", case_sensitive=False)
    validate_scalar(str, "prefix ABC suffix", matches=re.compile("abc", re.IGNORECASE), case_sensitive=True)
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "prefix abc suffix", matches="^abc$")


@pytest.mark.parametrize("pattern", ["(", "", b"abc", re.compile(b"abc")])
def test_invalid_regex_operands_raise_definition_errors(pattern):
    with pytest.raises(ConfValidationError):
        validate_scalar(str, "abc", matches=pattern)
