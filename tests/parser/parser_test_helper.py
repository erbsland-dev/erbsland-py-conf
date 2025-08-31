#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import pytest

from erbsland.conf.document import Document
from erbsland.conf.name_path import NamePath
from erbsland.conf.parser import load
from erbsland.conf.value import Value


RE_TRIM_MICROSECONDS = re.compile(r"(?<=\.\d{6})\d+(?=\D|$)")


@dataclass(frozen=True, slots=True)
class TestValue:
    name_path: str
    type_name: str
    value: str

    def compare_with(self, expected_value: TestValue):
        if self.type_name != expected_value.type_name:
            pytest.fail(
                f"For {self.name_path}: Type mismatch (actual != expected): {self.type_name} != {expected_value.type_name}"
            )
        if self.type_name == "Float":
            self._compare_float(expected_value)
            return
        if self.value != expected_value.value:
            self._fail(expected_value)

    DEFAULT_REL_TOL = 1e-9
    DEFAULT_ABS_TOL = 1e-10
    LARGE_THRESHOLD = 1e307

    def _compare_float(self, expected_value: TestValue):
        try:
            a = float(self.value)
            b = float(expected_value.value)
        except ValueError:
            self._fail(expected_value)
        # Handle NaNs explicitly: NaN never equals anything (including NaN)
        if math.isnan(b):
            if not math.isnan(a):
                self._fail(expected_value)
            return  # match
        # Accept inf/-inf with large finite values (> 1e+307) of same sign
        # If one is infinite and the other is a large finite with matching sign, accept
        if math.isinf(a) and not math.isinf(b):
            if (b > self.LARGE_THRESHOLD and a > 0) or (b < -self.LARGE_THRESHOLD and a < 0):
                return  # treat as acceptable match
            self._fail(expected_value)
        if math.isinf(b) and not math.isinf(a):
            if (a > self.LARGE_THRESHOLD and b > 0) or (a < -self.LARGE_THRESHOLD and b < 0):
                return  # treat as acceptable match
            self._fail(expected_value)
        # If both infinite, require the same sign
        if math.isinf(a) and math.isinf(b):
            if (a > 0 and b > 0) or (a < 0 and b < 0):
                return
            self._fail(expected_value)
        # Relative/absolute tolerance check
        diff = abs(a - b)
        max_ab = max(abs(a), abs(b))
        rel_tol = self.DEFAULT_REL_TOL
        abs_tol = self.DEFAULT_ABS_TOL
        if diff > max(rel_tol * max_ab, abs_tol):
            self._fail(expected_value)
        # Accept if within either relative or absolute tolerance

    def _fail(self, expected_value: TestValue) -> NoReturn:
        pytest.fail(f"For {self.name_path}: Expected value {expected_value.value}, got {self.value}")
        raise Exception("Unreachable")  # For type checking

    @staticmethod
    def _trim_microseconds(text: str) -> str:
        return RE_TRIM_MICROSECONDS.sub("", text)


class ParserTestHelper:

    RE_TEST_VALUE = re.compile(r"^(\w+)\((.*)\)$")

    @staticmethod
    def _test_file_path(file_name) -> Path:
        """
        Return the path to the test file with the given name.
        """
        return Path(__file__).parent / "data" / file_name

    def parse_file(self, file_name: str):
        """
        Parse the given file and store the result in the `doc` attribute.
        """
        self.doc = load(self._test_file_path(file_name))

    def parser_test_suite_path(self, path: Path):
        """
        Parse the given test suite file.
        """
        self.doc = load(path)

    def _parse_test_value(self, name_path: str, value: str) -> TestValue:
        match = self.RE_TEST_VALUE.match(value)
        if match:
            type_name, value = match.groups()
            return TestValue(name_path, type_name, value)
        else:
            raise ValueError(f"Invalid test value format: {name_path} = ??? => {value}")

    def validate_doc(self, expected_result: dict[str, str]):
        """
        Validate the parsed document against the expected result.
        """
        assert self.doc is not None
        assert isinstance(self.doc, Document)
        flat_map = self.doc.to_flat_dict()
        for name_path_str, expected_text in expected_result.items():
            name_path = NamePath.from_text(name_path_str)
            expected_test_value = self._parse_test_value(name_path_str, expected_text)
            assert (
                name_path in flat_map
            ), f"The parsed document lacks a expected value: {name_path_str} = {expected_text}"
            actual_value = flat_map[name_path]
            assert isinstance(actual_value, Value)
            actual_test_value = self._parse_test_value(name_path_str, actual_value.to_test_text())
            actual_test_value.compare_with(expected_test_value)
        for name_path in flat_map.keys():
            name_path_text = name_path.to_text()
            if name_path_text not in expected_result:
                expected_str = "\n".join(f"    {n} = {v}" for n, v in sorted(expected_result.items()))
                actual_str = "\n".join(f"    {n.to_text()} = {v.to_test_text()}" for n, v in sorted(flat_map.items()))
                pytest.fail(
                    f"The parsed document lacks a expected value: `{name_path_text}`.\n"
                    f"Expected values:\n{expected_str}\n"
                    f"Actual values:\n{actual_str}"
                )
