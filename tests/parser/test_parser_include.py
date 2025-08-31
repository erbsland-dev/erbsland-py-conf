#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import pytest

from erbsland.conf.error import ConfSyntaxError
from parser.parser_test_helper import ParserTestHelper


class TestParserInclude(ParserTestHelper):
    def test_basic_include(self):
        self.parse_file("include_basic/main.elcl")
        expected_result = {
            "main": "SectionWithNames()",
            "main.value_01": "Integer(5001)",
            "main.value_02": "Integer(5002)",
            "second": "SectionWithNames()",
            "second.value_03": "Integer(6001)",
            "sub_01": "SectionWithNames()",
            "sub_01.value_04": "Integer(7001)",
            "sub_01.value_05": "Integer(7002)",
            "sub_02": "SectionWithNames()",
            "sub_02.value_06": "Integer(8001)",
            "sub_02.value_07": "Integer(8002)",
            "sub_03": "SectionWithNames()",
            "sub_03.value_08": "Integer(9001)",
            "sub_03.value_09": "Integer(9002)",
        }
        self.validate_doc(expected_result)

    def test_recursive_include_order(self):
        self.parse_file("include_recursive/main.elcl")
        expected_result = {
            "block": "SectionList()",
            "block[0]": "SectionWithNames()",
            "block[0].value_01": "Integer(123)",
            "block[1]": "SectionWithNames()",
            "block[1].value_04": "Integer(123)",
            "block[2]": "SectionWithNames()",
            "block[2].value_02": "Integer(123)",
            "block[3]": "SectionWithNames()",
            "block[3].value_03": "Integer(123)",
        }
        self.validate_doc(expected_result)

    def test_include_not_found(self):
        self.parse_file("include_not_found/main.elcl")
        assert len(self.doc) == 0

    @pytest.mark.parametrize(
        "file_name",
        [
            "include_no_match1/main.elcl",
            "include_no_match2/main.elcl",
        ],
    )
    def test_no_wildcard_matches(self, file_name):
        self.parse_file(file_name)
        assert len(self.doc) == 0

    def test_error_loop(self):
        with pytest.raises(ConfSyntaxError):
            self.parse_file("include_loop/main.elcl")

    def test_error_nesting_limit(self):
        with pytest.raises(ConfSyntaxError):
            self.parse_file("include_nesting_limit/main.elcl")
