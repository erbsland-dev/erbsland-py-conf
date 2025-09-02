#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from pathlib import Path


from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.location import Position
from lexer.lexer_helper import LexerHelper


class TestLexerAssignment(LexerHelper):

    def test_lexer_reports_correct_token_positions(self):
        path = Path(__file__).parent / "data" / "single_values.elcl"
        content = path.read_text()
        self.setup_generator(path)

        index = 0
        expected_line = 1
        expected_column = 1
        expected_index = 0
        for token in self.tokenGenerator:
            if token.type == TokenType.END_OF_DATA:
                break
            expected_begin_pos = Position(expected_line, expected_column, expected_index)
            token_length = token.end.column - token.begin.column
            expected_end_pos = Position(expected_line, expected_column + token_length, expected_index + token_length)
            raw_text = token.raw_text
            assert token_length > 0
            assert token.begin == expected_begin_pos
            assert token.end == expected_end_pos
            assert len(raw_text) == token_length
            assert content[index : index + token_length] == raw_text
            expected_column += token_length
            expected_index += token_length
            index += token_length
            if "\n" in raw_text:
                expected_line += 1
                expected_column = 1
