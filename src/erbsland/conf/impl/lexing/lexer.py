#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.lexing.assignment import RE_NAME_ASSIGNMENT, RE_NAME_ASSIGMENT_ERROR_INDENTATION
from erbsland.conf.impl.lexing.assignment import handle_name_assigment_error_indentation, handle_tokens_from_assignment
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.rule import GeneratorRule
from erbsland.conf.impl.lexing.section import RE_SECTION_ERROR_INDENTATION, RE_SECTION_START
from erbsland.conf.impl.lexing.section import handle_tokens_from_section, handle_section_error_indentation
from erbsland.conf.impl.lexing.spacing import RE_EMPTY_LINE, RE_INDENTATION
from erbsland.conf.impl.lexing.spacing import handle_empty_line
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.source import Source


def handle_unexpected_indentation(cursor: Cursor, match) -> None:
    """
    Handle unexpected indentation by raising a syntax error.

    :param cursor: The cursor to report the error on.
    :param match: The (not used) match object from a `RE_SECTION_ERROR_INDENTATION` regex.
    """

    cursor.syntax_error("Sections and value names must not be indented")


class Lexer:
    """
    A lexer that produces tokens from a source.

    The lexer produces tokens for the full text from the source (including spacing and comments), so it can not only
    be used for parsing, but also as a base for syntax highlighting.
    """

    CORE_RULES: list[GeneratorRule] = [
        GeneratorRule(RE_EMPTY_LINE, handle_empty_line),
        GeneratorRule(RE_SECTION_ERROR_INDENTATION, handle_section_error_indentation),
        GeneratorRule(RE_SECTION_START, handle_tokens_from_section),
        GeneratorRule(RE_NAME_ASSIGMENT_ERROR_INDENTATION, handle_name_assigment_error_indentation),
        GeneratorRule(RE_NAME_ASSIGNMENT, handle_tokens_from_assignment),
        GeneratorRule(RE_INDENTATION, handle_unexpected_indentation),
    ]

    def __init__(self, source: Source, *, digest_enabled: bool = False, syntax_mode: bool = False):
        """
        Initialize the lexer.

        :param source: The open source to read tokens from. Must be opened and closed by the caller.
        :param digest_enabled: Whether to enable digest calculation of the source.
        :param syntax_mode: Create error tokens instead of raising exceptions. Try to continue lexing
            after an error token is encountered.
        """
        self._cursor = Cursor(source, digest_enabled=digest_enabled, syntax_mode=syntax_mode)

    def tokens(self) -> TokenGenerator:
        """
        Generate tokens from the source.

        Yields tokens until the source is exhausted and ends with an ``END_OF_DATA`` token.

        :raises Error: If a parsing error occurs.
        """
        self._cursor.initialize()
        while self._cursor.has_more_content():
            try:
                yield from self._process_line()
            except Error as e:
                if self._cursor.syntax_mode and e.category != ErrorCategory.IO:
                    yield from self._cursor.error_tokens_from_error(e)
                    if token := self._cursor.recover_at_next_line():  # Try resuming at the next line.
                        yield token
                else:
                    raise
        yield Token(TokenType.END_OF_DATA)
        return None

    def _process_line(self) -> TokenGenerator:
        for rule in self.CORE_RULES:
            assert rule.handler is not None
            if match := self._cursor.match(rule.pattern):
                for token in rule.handler(self._cursor, match):
                    if token.type == TokenType.ERROR:
                        self._cursor.syntax_error(token.value)
                    yield token
                return  # Stop at a match
        self._cursor.syntax_error("Unexpected content. Expected a section start, name assignment, or empty line")
