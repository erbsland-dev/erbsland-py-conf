#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


r"""
Utilities to escape and unescape single-line text according to the ELCL rules.

Besides general *text* escaping, this module also provides helpers for rendering text names inside name paths.
These follow the stricter escaping rules described in
``language_reference/reference/name-path/text-names-for-parsers.md`` and use ``\u{...}`` sequences exclusively.
"""


from __future__ import annotations

import re


def escape_text(text: str) -> str:
    """Escape ``text`` according to the ELCL text rules."""

    result: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == "\\":
            result.append("\\\\")
        elif ch == '"':
            result.append('\\"')
        elif ch == "$":
            result.append("\\$")
        elif ch == "\n":
            result.append("\\n")
        elif ch == "\r":
            result.append("\\r")
        elif ch == "\t":
            result.append("\\t")
        elif cp == 0 or cp < 0x20 or (0x7F <= cp <= 0x9F):
            result.append(f"\\u{{{cp:x}}}")
        else:
            result.append(ch)
    return "".join(result)


def escape_text_for_test(text: str) -> str:
    """Escape ``text`` using the strict rules employed by unit tests."""

    result: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp <= 0x1F or cp >= 0x7F or ch in ["\\", '"', ".", ":", "="]:
            result.append(f"\\u{{{cp:x}}}")
        else:
            result.append(ch)
    return "".join(result)


def escape_name_path_text(text: str) -> str:
    r"""
    Escape ``text`` for use as a quoted text-name in a name path.

    All control characters (U+0000–U+001F) and every character outside the ASCII range (U+007F–U+10FFFF) are escaped.
    In addition, the characters ``\\``, ``"``, ``.``, ``:`` and ``=`` are always escaped.
    The ``\\u{...}`` form is used for all escapes.

    This differs from :func:`escape_text` which may use shorthand escapes
    like ``\n`` or ``\t`` and also escapes the dollar sign ``$``.  Name
    path text requires a stricter form so that the resulting name can be
    round-tripped through the parser without ambiguity.
    """
    result: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x20 or cp >= 0x7F or ch in ["\\", '"', ".", ":", "="]:
            result.append(f"\\u{{{cp:x}}}")
        else:
            result.append(ch)
    return "".join(result)


RE_TEXT_ESCAPE = re.compile(
    r"""(?xsi)
    \\
    (?P<escaped_expr>
        u \{ (?P<uni2> [0-9a-f]* ) \}
    |
        u (?P<uni1> [0-9a-f]{0,4} )
    |
        .
    )?
    """
)


class UnescapeError(Exception):
    """A special exception raised when unescaping text fails."""

    def __init__(self, message: str, offset: int):
        super().__init__(message)
        self.offset = offset


UNESCAPE_MAP = {
    "\\": "\\",
    '"': '"',
    "$": "$",
    "n": "\n",
    "N": "\n",
    "r": "\r",
    "R": "\r",
    "t": "\t",
    "T": "\t",
}


def _unescape_text_match(match: re.Match[str]) -> str:
    escaped_expr = match.group("escaped_expr")
    if not escaped_expr:
        raise UnescapeError("Unexpected end after backslash", match.start())
    uni1 = match.group("uni1")
    uni2 = match.group("uni2")
    if uni1 or uni2:
        if uni1 is not None:
            if len(uni1) != 4:
                raise UnescapeError("Expected 4 hex digits", match.start())
        if uni2 is not None:
            if not (1 <= len(uni2) <= 8):
                raise UnescapeError("1-8 hex digits are allowed", match.start())
        cp = int(uni1 or uni2, 16)
        if cp == 0 or cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
            raise UnescapeError("Invalid Unicode code point", match.start())
        return chr(cp)
    if repl := UNESCAPE_MAP.get(match.group("escaped_expr"), None):
        return repl
    raise UnescapeError("Unknown escape sequence", match.start())


def unescape_text(content: str) -> str:
    """Unescape ``content`` according to the ELCL text rules."""

    return RE_TEXT_ESCAPE.sub(_unescape_text_match, content)


RE_REGEX_ESCAPE = re.compile(r"(?xs)\\(?P<char>.)?")


def _unescape_regex_match(match: re.Match[str]) -> str:
    ch = match.group("char")
    if ch is None:
        raise UnescapeError("Unexpected end after backslash", match.start())
    if ch == "/":
        return "/"
    # Keep unknown escapes as-is: backslash + char
    return "\\" + ch


def unescape_regex(content: str) -> str:
    r"""
    Unescape regex content according to ELCL regex rules for single-line values.

    Behavior (mirrors unescape_text implementation style):
    - \/ → '/'
    - \\ → '\\'
    - Any other backslash sequence remains unchanged ("\\x" stays "\\x").
    - A trailing solitary backslash raises UnescapeError with the correct offset.
    """
    return RE_REGEX_ESCAPE.sub(_unescape_regex_match, content)
