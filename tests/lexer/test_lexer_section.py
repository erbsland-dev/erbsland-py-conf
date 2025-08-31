#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import pytest

from erbsland.conf.error import Error
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name, RegularName, TextName
from lexer.lexer_helper import LexerHelper


class TestLexerSection(LexerHelper):

    def test_minimal_section(self):
        self.setup_generator("[main]")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_end_of_stream()

        self.setup_generator("-[main]-")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="-[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]-")
        self.expect_end_of_stream()

        self.setup_generator("*[main]")
        self.expect_token(TokenType.SECTION_LIST_OPEN, expected_raw="*[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_LIST_CLOSE, expected_raw="]")
        self.expect_end_of_stream()

        self.setup_generator("*[main]*")
        self.expect_token(TokenType.SECTION_LIST_OPEN, expected_raw="*[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_LIST_CLOSE, expected_raw="]*")
        self.expect_end_of_stream()

        self.setup_generator("-*[main]*-")
        self.expect_token(TokenType.SECTION_LIST_OPEN, expected_raw="-*[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_LIST_CLOSE, expected_raw="]*-")
        self.expect_end_of_stream()

    @pytest.mark.parametrize(
        "pattern",
        [
            "[%(section_text)s]",
            "----[%(section_text)s]----",
            "[ %(section_text)s ]",
            "[\t%(section_text)s\t]",
            "[  \t  %(section_text)s   \t ]",
            "[%(section_text)s]\n",
            "[%(section_text)s]    \n",
            "[%(section_text)s]    # comment\n",
        ],
    )
    @pytest.mark.parametrize(
        "section_text, expected_name_path",
        [
            ("main", [RegularName("main")]),  # Repeat the last test to verify this test
            ("   \t main  \t\t  ", [RegularName("main")]),
            ("main.sub", [RegularName("main"), RegularName("sub")]),
            ("main.sub.sub", [RegularName("main"), RegularName("sub"), RegularName("sub")]),
            ("main   .    sub    .   sub", [RegularName("main"), RegularName("sub"), RegularName("sub")]),
            ("Two Words", [RegularName("two_words")]),
            ("Two120 10Words", [RegularName("two120_10words")]),
            ("Two Words   . Another Name Two", [RegularName("two_words"), RegularName("another_name_two")]),
            ('text."  This is a text  "', [RegularName("text"), TextName("  This is a text  ")]),
            ('text  .\t "  This is a text  "', [RegularName("text"), TextName("  This is a text  ")]),
            ('text."\\r\\n\\u{0020}"', [RegularName("text"), TextName("\r\n ")]),
        ],
    )
    def test_absolute_sections(self, pattern, section_text, expected_name_path):
        self.setup_generator(pattern % {"section_text": section_text})
        self.expect_token(TokenType.SECTION_MAP_OPEN)
        for index, name in enumerate(expected_name_path):
            token = next(self.tokenGenerator)
            while token.type == TokenType.SPACING:
                token = next(self.tokenGenerator)
            assert token.type == TokenType.NAME
            assert token.value == name
            if index < len(expected_name_path) - 1:
                token = next(self.tokenGenerator)
                while token.type == TokenType.SPACING:
                    token = next(self.tokenGenerator)
                assert token.type == TokenType.NAME_PATH_SEPARATOR
        token = next(self.tokenGenerator)
        while token.type == TokenType.SPACING:
            token = next(self.tokenGenerator)
        assert token.type == TokenType.SECTION_MAP_CLOSE
        # Ignore the end of the stream.

    @pytest.mark.parametrize(
        "section_text, expected_name_path",
        [
            (".main", [RegularName("main")]),  # Repeat the last test to verify this test
            ("  . \t main  \t\t  ", [RegularName("main")]),
            (".main.sub", [RegularName("main"), RegularName("sub")]),
            (".main.sub.sub", [RegularName("main"), RegularName("sub"), RegularName("sub")]),
            ("  .  main   .    sub    .   sub    ", [RegularName("main"), RegularName("sub"), RegularName("sub")]),
            ("  . Two Words", [RegularName("two_words")]),
            ("  . Two120 10Words", [RegularName("two120_10words")]),
            (" .  Two Words   ", [RegularName("two_words")]),
            (" . Two Words   . Another Name Two   ", [RegularName("two_words"), RegularName("another_name_two")]),
            ('.text."  This is a text  "', [RegularName("text"), TextName("  This is a text  ")]),
            (' . \t "  This is a text  " \t', [TextName("  This is a text  ")]),
            (' . "\\r\\n\\u{0020}"', [TextName("\r\n ")]),
        ],
    )
    def test_relative_sections(self, section_text, expected_name_path):
        self.setup_generator(f"[{section_text}]")
        self.expect_token(TokenType.SECTION_MAP_OPEN)
        token = next(self.tokenGenerator)
        while token.type == TokenType.SPACING:
            token = next(self.tokenGenerator)
        assert token.type == TokenType.NAME_PATH_SEPARATOR
        for index, name in enumerate(expected_name_path):
            token = next(self.tokenGenerator)
            while token.type == TokenType.SPACING:
                token = next(self.tokenGenerator)
            assert token.type == TokenType.NAME
            assert token.value == name
            if index < len(expected_name_path) - 1:
                token = next(self.tokenGenerator)
                while token.type == TokenType.SPACING:
                    token = next(self.tokenGenerator)
                assert token.type == TokenType.NAME_PATH_SEPARATOR
        token = next(self.tokenGenerator)
        while token.type == TokenType.SPACING:
            token = next(self.tokenGenerator)
        assert token.type == TokenType.SECTION_MAP_CLOSE
        self.expect_end_of_stream()

    def test_unexpected_content_after_section(self):
        self.setup_generator("[main] trailing")
        with pytest.raises(Error, match="Unexpected content after the section, expected end of line"):
            token = next(self.tokenGenerator)
            while token.type != TokenType.END_OF_DATA:
                token = next(self.tokenGenerator)

    @pytest.mark.parametrize(
        "end_of_document",
        [
            "",
            "\n",
            "\r\n",
            "    ",
            "\t",
            "    \n",
            "\t\n",
            "# comment\n",
            "    # comment\n",
            "\t# comment\n",
        ],
    )
    @pytest.mark.parametrize(
        "document",
        [
            "[",
            "[]",
            "[   ]",
            "   [main]",
            "[main",
            "[    main",
            "[main.",
            "[    main.",
            "[    main    .",
            "[main.sub",
            "[    main.sub",
            "[    main . sub",
            "[main.]",
            "[main..]",
            "[main..sub]",
            "[main . . sub]",
            "[main . . . sub]",
            "[main\tmain]",
            '[main "text"]',
            "[.",
            "[.]",
            "[ .]",
            "[ . ]",
            "[.main",
            "[    .main",
            "[    .    main",
            '[text."',
            '[text.    "',
            '[text."text',
            '[text."text\\',
            "[main]*",
            "-- [main] --",
            "- -[main]- -",
            "-- [main]*--",
            "--* [main] *--",
            "-- *[main]* --",
            "- -*[main]*- -",
            "[a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p]",
            "[main.@version]",
            "[@feature]",
            '["text"]',
            '[text."text".@version]',
            "[123]",
            "[name_]",
            "[_name]",
            "[@123]",
            "[Hello This_]",
        ],
    )
    def test_section_errors(self, end_of_document, document):
        """
        Test section errors.
        Could be better. But at least we get some coverage.
        """
        self.setup_generator(document + end_of_document)
        with pytest.raises(Error):
            token = next(self.tokenGenerator)
            while token.type != TokenType.END_OF_DATA:
                token = next(self.tokenGenerator)
