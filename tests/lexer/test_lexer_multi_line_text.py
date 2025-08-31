#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerMultiLineText(LexerHelper):
    def test_valid_multi_line_text(self):
        content = '"""\n    First line\n    Second line\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="First line", expected_value="First line")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="Second line", expected_value="Second line")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_empty_multi_line_text(self):
        # No content lines; just open, newline, indentation, close.
        content = '"""\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_comment_after_open_bracket(self):
        # Spaces and a comment are allowed after the opening quotes.
        content = '"""  # comment after open\n    line\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.SPACING, expected_raw="  ")
        self.expect_token(TokenType.COMMENT, expected_raw="# comment after open")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="line", expected_value="line")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_spaces_after_open_bracket(self):
        # Only spaces after the opening quotes are allowed before the newline.
        content = '"""   \n    line\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.SPACING, expected_raw="   ")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="line", expected_value="line")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_empty_lines_without_indentation(self):
        # Empty lines are allowed without indentation in between content lines.
        content = '"""\n\n    first\n\n    second\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # first empty line
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # second empty line
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="first", expected_value="first")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # empty line between content lines
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="second", expected_value="second")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_ignored_indented_end_sequence(self):
        # A triple quote that is not at the exact indentation is content, not a close.
        # Keep the indentation pattern consistent (4 spaces), add extra space/tab AFTER the indentation.
        content = '"""\n    text\n     """\n    text\n    \t"""\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="text", expected_value="text")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        # Line with one additional leading space before the quotes → part of content.
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw=' """', expected_value=' """')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        # Line with a tab before the quotes (but after the base indentation) → part of content.
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="text", expected_value="text")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw='\t"""', expected_value='\t"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        # Properly closed at exact indentation.
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_escape_sequences(self):
        # All escapes valid for single-line text are valid here.
        content = (
            '"""\n' '    \\"\\n\\r\\$\\u{41}●🄴\\u0041\\\\\n' '    "" this is not the end\n' '    \\"""\n' '    """'
        )
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(
            TokenType.MULTI_LINE_TEXT,
            expected_raw='\\"\\n\\r\\$\\u{41}●🄴\\u0041\\\\',
            expected_value='"\n\r$A●🄴A\\',
        )
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(
            TokenType.MULTI_LINE_TEXT,
            expected_raw='"" this is not the end',
            expected_value='"" this is not the end',
        )
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        # A backslash before the triple quotes keeps them as content.
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw='\\"""', expected_value='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_unicode_and_quotes_allowed(self):
        content = (
            '"""\n'
            "    “Hello!” exclaimed the multi-line text,\n"
            '    彼は興奮した様子で言った："ダブルクオート文字はここで使える！"\n'
            '    """'
        )
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(
            TokenType.MULTI_LINE_TEXT,
            expected_raw="“Hello!” exclaimed the multi-line text,",
            expected_value="“Hello!” exclaimed the multi-line text,",
        )
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        expected = '彼は興奮した様子で言った："ダブルクオート文字はここで使える！"'
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw=expected, expected_value=expected)
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_tabs_and_mixed_indentation(self):
        # Base indentation is a tab; deeper indentation becomes part of the content.
        content = '"""\n\ttext\n\t\t    deeper\n\t"""'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="\t")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="text", expected_value="text")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="\t")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="\t    deeper", expected_value="\t    deeper")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="\t")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_comment_after_close(self):
        # Spaces and a comment after the closing quotes are allowed on the line.
        content = '"""\n    line\n    """   # done'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="line", expected_value="line")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_token(TokenType.SPACING, expected_raw="   ")
        self.expect_token(TokenType.COMMENT, expected_raw="# done")
        self.expect_value_end()

    def test_next_line_multiline_text_basic(self):
        # value on next line with 4-space indentation before opening quotes
        content = '\n    """\n    first\n    """'
        self.setup_for_value(content)
        # Prefix up to name/value separator and trailing space
        self.expect_value_begin()
        # Next-line style: end-of-line, then indentation before open
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="first", expected_value="first")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    def test_next_line_first_line_has_inner_spacing(self):
        # value on next line with a 1-space indentation pattern; first text line includes extra spaces
        content = '\n """\n    text\n """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw=" ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw=" ")
        # Remaining three spaces are part of content (kept literally)
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="   text", expected_value="   text")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw=" ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            (
                '"""\n    First line\n  second line\n    """',
                ErrorCategory.INDENTATION,
            ),
            (
                '"""\n    bad \\x escape\n    """',
                ErrorCategory.SYNTAX,
            ),
            (
                '"""\n    unterminated',
                ErrorCategory.UNEXPECTED_END,
            ),
            (
                '"""\n    bad control: \x01\n    """',
                ErrorCategory.CHARACTER,
            ),
            (
                '"""\n    text\n    ///\n',
                ErrorCategory.UNEXPECTED_END,
            ),
        ],
    )
    def test_invalid_multi_line_text(self, content, expected_category):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            assert e.category == expected_category

    def test_crlf_line_breaks(self):
        # Support Windows-style CRLF line breaks in the content.
        content = '"""\r\n    a\r\n    """'
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_TEXT_OPEN, expected_raw='"""')
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\r\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT, expected_raw="a", expected_value="a")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\r\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_TEXT_CLOSE, expected_raw='"""')
        self.expect_value_end()
