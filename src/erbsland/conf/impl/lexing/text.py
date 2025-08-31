#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import re
from typing import Callable

from erbsland.conf.impl.lexing.common_value import REP_VALID_END_OF_VALUE
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.spacing import scan_for_end_of_line, scan_for_indentation, expect_end_of_line
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.text_escape import unescape_text, UnescapeError, unescape_regex
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Match anything that looks like single-line text, including an incomplete text without closing quotes.
RE_SINGLE_LINE_TEXT = re.compile(
    rf"""(?x)
    (?P<open_quote>    "                       ) 
    (?P<text>          (?: [^"\\\n\r] | \\. )* ) 
    (?P<close_quote>   " | \Z                  )
    {REP_VALID_END_OF_VALUE}
    """
)

# Match anything that looks like single-line code, including an incomplete code without closing quotes.
RE_SINGLE_LINE_CODE = re.compile(
    rf"""(?x)
    (?P<open_quote>    `                       ) 
    (?P<text>          [^`\n\r]*               ) 
    (?P<close_quote>   ` | \Z                  )
    {REP_VALID_END_OF_VALUE}
    """
)

# Match anything that looks like single-line regex, including an incomplete regex without closing quotes.
RE_SINGLE_LINE_REGEX = re.compile(
    rf"""(?x)
    (?P<open_quote>    /                       ) 
    (?P<text>          (?: [^/\\\n\r] | \\. )* ) 
    (?P<close_quote>   / | \Z                  )
    {REP_VALID_END_OF_VALUE}
    """
)

# Match the opening quotes for multi-line text.
RE_MULTI_LINE_TEXT_OPEN = re.compile(
    r"""(?x)
    (?P<open_quote>    \"{3}                   )
    """
)

# Match the opening quotes for multi-line code with an optional language identifier.
RE_MULTI_LINE_CODE_OPEN = re.compile(
    r"""(?x)
    (?P<open_quote>    `{3}                    )
    (?P<lang_id>       [a-z][-_a-z0-9]{0,15}   )?
    """
)

# Match the opening quotes for multi-line regex.
RE_MULTI_LINE_REGEX_OPEN = re.compile(
    r"""(?x)
    (?P<open_quote>    /{3}                    )
    """
)

# Match any type of closing quote for multi-line text, code or regex.
RE_MULTI_LINE_CLOSE = re.compile(
    r"""(?x)
    (?P<close_quote>    [`/\"]{3}              )
    """
)

# Match an empty line inside multi-line text that contains only spacing and no comments.
RE_EMPTY_TEXT_LINE = re.compile(
    r"""(?x)
    (?P<eol_whitespace>    [\x20\t]*    )
    (?P<eol_line_break>    \r? \n       )? # optional line break (may be the last token)
    \Z
    """
)

# For multi-line regex, split the text part from any trailing spacing and comment part.
RE_TEXT_COMMENT_SPLIT = re.compile(
    r"""(?x)
    \A
    (?P<text>
        (?: \\ . | [^\\#] )*
    ) 
    (?P<comment>
        \# .*
    )
    \Z
    """
)


def scan_for_text(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """Convert a quoted text match into a token."""

    try:
        text = unescape_text(match.group("text"))
        if not match.group("close_quote"):
            return cursor.error_token(match.group(), "Text with missing closing quote")
        return cursor.token(TokenType.TEXT, match.group(), text)
    except UnescapeError as error:
        cursor.syntax_error(f"Invalid escape sequence: {error}", offset=error.offset)


def scan_for_code(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """Convert a quoted single-line code fragment into a token."""

    if not match.group("close_quote"):
        return cursor.error_token(match.group(), "Code with missing closing quote")
    return cursor.token(TokenType.CODE, match.group(), match.group("text"))


def scan_for_regex(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """
    Convert a quoted single-line regular expression into a token.

    Also checking anc compiling the regular expression.
    """

    try:
        if not match.group("close_quote"):
            return cursor.error_token(match.group(), "Regex with missing closing quote")
        re_text = unescape_regex(match.group("text"))
        compiled_re = re.compile(re_text)
        return cursor.token(TokenType.REG_EX, match.group(), compiled_re)
    except UnescapeError as error:
        cursor.syntax_error(f"Invalid escape sequence: {error}", offset=error.offset)
    except re.error as error:  # re.error for Python < 3.13
        cursor.syntax_error(f"Invalid regular expression: {error}")


def scan_for_empty_text_line(cursor: Cursor) -> list[Token]:
    """Return tokens for an empty line inside multi-line text."""

    if match := cursor.match(RE_EMPTY_TEXT_LINE):
        tokens = []
        if raw_text := match.group("eol_whitespace"):
            tokens.append(cursor.token(TokenType.SPACING, raw_text))
        if raw_text := match.group("eol_line_break"):
            tokens.append(cursor.token(TokenType.LINE_BREAK, raw_text))
        return tokens
    return []


def scan_for_multi_line_close(cursor: Cursor, quote_str: str, close_token: TokenType) -> Token | None:
    """Return the closing token for a multi-line value if present."""

    if match := cursor.match(RE_MULTI_LINE_CLOSE):
        if match.group("close_quote") == quote_str:
            return cursor.token(close_token, match.group())
    return None


def _handle_multi_line_content(
    cursor: Cursor, quote_str: str, text_token: TokenType, close_token: TokenType, unescape_fn: Callable | None
) -> TokenGenerator:
    """Yield the body tokens of a multi-line value until its closing marker."""

    cursor.expect_next_line("Expected additional lines with multi-line content after the opening quote")
    while True:
        if tokens := scan_for_empty_text_line(cursor):
            yield from tokens
            cursor.expect_next_line("Expected additional lines with multi-line content")
            continue
        if token := scan_for_indentation(cursor):
            yield token
        else:
            cursor.syntax_error("Expected indentation or empty line to continue the multi-line content")
        if token := scan_for_multi_line_close(cursor, quote_str, close_token):
            yield token
            yield from expect_end_of_line(cursor, "Expected end of line after the closing quote")
            break
        text = cursor.raw_text_to_eol().rstrip(" \t\r\n")
        if text:
            if unescape_fn is None:
                unescaped_text = text
            else:
                try:
                    unescaped_text = unescape_fn(text)
                except UnescapeError as error:
                    cursor.syntax_error(f"Invalid escape sequence: {error}", offset=error.offset)
            yield cursor.token(text_token, text, unescaped_text)
        yield from scan_for_end_of_line(cursor)
        cursor.expect_next_line("Expected additional lines with multi-line content")
    return


def handle_multi_line_text(cursor: Cursor, match: re.Match[str]) -> TokenGenerator:
    """Handle a multi-line text value."""

    yield cursor.token(TokenType.MULTI_LINE_TEXT_OPEN, match.group())
    yield from expect_end_of_line(cursor, "Expected end of line after the opening multi-line text quote")
    yield from _handle_multi_line_content(
        cursor, '"""', TokenType.MULTI_LINE_TEXT, TokenType.MULTI_LINE_TEXT_CLOSE, unescape_text
    )


def handle_multi_line_code(cursor: Cursor, match: re.Match[str]) -> TokenGenerator:
    """Handle a multi-line code block."""

    yield cursor.token(TokenType.MULTI_LINE_CODE_OPEN, match.group("open_quote"))
    if lang_id := match.group("lang_id"):
        yield cursor.token(TokenType.MULTI_LINE_CODE_LANGUAGE, lang_id)
    yield from expect_end_of_line(cursor, "Expected end of line after the opening multi-line code quote")
    yield from _handle_multi_line_content(
        cursor, "```", TokenType.MULTI_LINE_CODE, TokenType.MULTI_LINE_CODE_CLOSE, None
    )


def handle_multi_line_regex(cursor: Cursor, match: re.Match[str]) -> TokenGenerator:
    """Handle a multi-line regular expression."""

    yield cursor.token(TokenType.MULTI_LINE_REGEX_OPEN, match.group())
    yield from expect_end_of_line(cursor, "Expected end of line after the opening multi-line regular expression quote")
    cursor.expect_next_line("Expected additional lines with multi-line regex after the opening quote")
    while True:
        if tokens := scan_for_empty_text_line(cursor):
            yield from tokens
            cursor.expect_next_line("Expected additional lines with multi-line content")
            continue
        if token := scan_for_indentation(cursor):
            yield token
        else:
            cursor.syntax_error("Expected indentation or empty line to continue the multi-line content")
        if token := scan_for_multi_line_close(cursor, "///", TokenType.MULTI_LINE_REGEX_CLOSE):
            yield token
            yield from expect_end_of_line(cursor, "Expected end of line after the closing quote")
            break
        text = cursor.raw_text_to_eol().rstrip(" \t\r\n")
        if text:
            # Strip any comment from the end of the text.
            if text_match := RE_TEXT_COMMENT_SPLIT.match(text):
                text = text[: text_match.start("comment")]
            try:
                unescaped_text = unescape_regex(text)
            except UnescapeError as error:
                cursor.syntax_error(f"Invalid escape sequence: {error}", offset=error.offset)
            yield cursor.token(TokenType.MULTI_LINE_REGEX, text, unescaped_text)
        yield from scan_for_end_of_line(cursor)
        cursor.expect_next_line("Expected additional lines with multi-line content")
    return
