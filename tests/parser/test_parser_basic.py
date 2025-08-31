#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from erbsland.conf.parser import loads, load
from parser.parser_test_helper import ParserTestHelper


class TestParserBasic(ParserTestHelper):

    @pytest.mark.parametrize(
        "file_name",
        [
            "basic_empty.elcl",
            "basic_only_comments.elcl",
            "basic_empty_with_meta.elcl",
        ],
    )
    def test_empty_document(self, file_name):
        self.parse_file(file_name)
        assert len(self.doc) == 0

    def test_small_document(self):
        self.parse_file("basic_small.elcl")
        expected_result = {
            "main": "SectionWithNames()",
            "main.connect": r'Text("host01\u{2e}example\u{2e}com")',
            "main.server_port": "Integer(1234)",
            "main.client": "SectionWithNames()",
            "main.client.name": 'Text(" example client ")',
            "main.client.welcome_message": r'Text("Hello user!\u{a}This is the welcome message\u{2e}\u{2e}\u{2e}")',
            "server": "SectionList()",
            "server[0]": "SectionWithNames()",
            "server[0].host": r'Text("host02\u{2e}example\u{2e}com")',
            "server[1]": "SectionWithNames()",
            "server[1].host": r'Text("host03\u{2e}example\u{2e}com")',
            "server[1].port": "Integer(65535)",
        }
        self.validate_doc(expected_result)

    def test_mixed_text_and_regular(self):
        self.parse_file("basic_mixed_text_and_regular.elcl")
        expected_result = {
            "main": "SectionWithNames()",
            "main.value1": "Integer(1)",
            "main.value2": "Integer(2)",
            "main.value3": "Integer(3)",
            "main.sub_text": "SectionWithTexts()",
            'main.sub_text."one"': "SectionWithNames()",
            'main.sub_text."one".value': "Integer(10)",
            'main.sub_text."two"': "SectionWithNames()",
            'main.sub_text."two".value': "Integer(20)",
            'main.sub_text."three"': "SectionWithNames()",
            'main.sub_text."three".value': "Integer(30)",
            "sub": "IntermediateSection()",
            "sub.sub": "IntermediateSection()",
            "sub.sub.sub": "SectionWithTexts()",
            'sub.sub.sub."one"': "SectionWithNames()",
            'sub.sub.sub."one".value': "Integer(101)",
            'sub.sub.sub."two"': "SectionWithNames()",
            'sub.sub.sub."two".value': "Integer(102)",
            'sub.sub.sub."three"': "SectionWithNames()",
            'sub.sub.sub."three".value': "Integer(103)",
            "text": "SectionWithTexts()",
            'text."one"': "SectionWithNames()",
            'text."one".value': "Integer(201)",
            'text."two"': "SectionWithNames()",
            'text."two".value': "Integer(202)",
            'text."three"': "SectionWithNames()",
            'text."three".value': "Integer(203)",
        }
        self.validate_doc(expected_result)
