#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.impl.value_storage_type import ValueStorageType, is_valid_storage_value
from erbsland.conf.location import Position
from erbsland.conf.name import Name


# Tokens can store all types value to, but also names.
TokenStorageType = ValueStorageType | Name


class Token:
    """
    Single lexical token.

    A token captures the textual representation of a syntactic element together with its location and,
    if applicable, its parsed value.
    """

    def __init__(
        self,
        token_type: TokenType,
        *,
        begin: Position = None,
        end: Position = None,
        raw_text: str = None,
        value: TokenStorageType = None,
    ):
        """
        Create a new token instance.

        :param token_type: The token category.
        :param begin: Optional start position of the token in the source text.
        :param end: Optional end position of the token in the source text.
        :param raw_text: The raw textual representation.
        :param value: Parsed value associated with the token. It can be either a primitive value or
            a :class:`erbsland.conf.name.Name`.
        """

        if not isinstance(token_type, TokenType):
            raise ValueError(f"'token_type' must be a TokenType, not {type(token_type)}")
        if begin and not isinstance(begin, Position):
            raise ValueError(f"'begin' must be a Position, not {type(begin)}")
        if end and not isinstance(end, Position):
            raise ValueError(f"'end' must be a Position, not {type(end)}")
        if raw_text and not isinstance(raw_text, str):
            raise ValueError(f"'raw_text' must be a string, not {type(raw_text)}")
        if value and not isinstance(value, Name) and not is_valid_storage_value(value):
            raise ValueError(f"Invalid type for token value: {type(value)}")
        self._type = token_type
        self._begin = begin
        self._end = end
        self._raw_text = raw_text
        self._value = value

    def __repr__(self):
        return f"Token({self._type.name}, {self._begin}-{self._end}, {self._value})"

    @property
    def type(self) -> TokenType:
        """The token's type."""

        return self._type

    @property
    def begin(self) -> Position:
        """Start position of the token in the source text."""

        return self._begin

    @property
    def end(self) -> Position:
        """End position of the token in the source text."""

        return self._end

    @property
    def raw_text(self) -> str:
        """The raw textual representation of the token."""

        return self._raw_text

    @property
    def value(self) -> TokenStorageType:
        """Parsed value associated with the token."""

        return self._value
