#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name
from lexer.lexer_helper import LexerHelper


class TestLexerAssignment(LexerHelper):

    def test_assignment_same_line_1(self):
        self.setup_generator("[main]\nvalue: 1  # comment\n")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(TokenType.INTEGER, expected_raw="1", expected_value=1)
        self.expect_token(TokenType.SPACING, expected_raw="  ")
        self.expect_token(TokenType.COMMENT, expected_raw="# comment")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    def test_assignment_same_line_2(self):
        self.setup_generator("[main]\nvalue    =1\n")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw="=")
        self.expect_token(TokenType.INTEGER, expected_raw="1", expected_value=1)
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    def test_assignment_next_line_1(self):
        self.setup_generator("[main]\nvalue: # comment\n    1  # another comment")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(TokenType.COMMENT, expected_raw="# comment")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.INTEGER, expected_raw="1", expected_value=1)
        self.expect_token(TokenType.SPACING, expected_raw="  ")
        self.expect_token(TokenType.COMMENT, expected_raw="# another comment")
        self.expect_end_of_stream()

    def test_assignment_next_line_2(self):
        self.setup_generator("[main]\nvalue    =\n\t1\n")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw="=")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="\t")
        self.expect_token(TokenType.INTEGER, expected_raw="1", expected_value=1)
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()
