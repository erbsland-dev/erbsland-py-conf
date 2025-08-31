#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import re
from pathlib import Path

import pytest

from erbsland.conf.error import Error
from parser.parser_test_helper import ParserTestHelper


TEST_SUITE_PATH = Path(__file__).parent.parent / "erbsland-lang-config-tests" / "tests" / "V1_0"
RE_OUTCOME_LINE = re.compile(r"^(.*) = (.*)\s*$")


class TestParserCompliance(ParserTestHelper):

    def test_is_test_suite_available(self):
        assert TEST_SUITE_PATH.exists()
        assert TEST_SUITE_PATH.is_dir()
        assert len(list(TEST_SUITE_PATH.rglob("*.elcl"))) > 100

    def test_parser_compliance(self, test_case_path: Path):
        outcome_file = test_case_path.with_suffix(".out")
        assert outcome_file.is_file()
        outcome = outcome_file.read_text()
        if "FAIL" in test_case_path.name:
            try:
                self.parser_test_suite_path(test_case_path)
                assert False, "Expected an error, but no error was raised"
            except Error as e:
                pass  # Test for the correct error category.
            except Exception as e:
                raise AssertionError(f"Unexpected exception: {e}") from e
        else:
            expected_result: dict[str, str] = {}
            for line in outcome.splitlines():
                if not line or line.startswith("#"):
                    continue
                match = RE_OUTCOME_LINE.match(line)
                assert match is not None, f"Invalid outcome line: {line}"
                key, value = match.groups()
                if key.startswith("@"):
                    continue  # Ignore meta-values, as our parser does not include them in the document.
                expected_result[key] = value
            self.parser_test_suite_path(test_case_path)
            self.validate_doc(expected_result)
