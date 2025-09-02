#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from erbsland.conf.location import Position


class PositionCounter:
    """Track the current line and column while reading text."""

    def __init__(self) -> None:
        """
        Initialize the counter at line ``0`` and column ``1``.

        The line number is set to zero because it is increased when a new line is read.
        As initially no line is read, the position is virtually *before* the first line.
        """

        self._character_index = 0
        self._line = 0
        self._column = 1

    @property
    def character_index(self) -> int:
        """Current character index into the source text from the start."""

        return self._character_index

    @property
    def line(self) -> int:
        """Current line number starting at ``1``."""

        return self._line

    @property
    def column(self) -> int:
        """Current column number starting at ``1``."""

        return self._column

    def position(self) -> Position:
        """Return the current position as a :class:`erbsland.conf.location.Position`."""

        return Position(self.line, self.column, self.character_index)

    def advance(self, columns: int = 1) -> None:
        """Advance the column counter by ``columns``."""

        self._character_index += columns
        self._column += columns

    def advance_line(self) -> None:
        """Move to the next line and reset the column to ``1``."""

        self._line += 1
        self._column = 1

    def __repr__(self) -> str:
        """Return a debug representation of the current position."""

        return f"Position({self.line}, {self.column})"  # pragma: no cover

    def __str__(self) -> str:
        """Return the position formatted as ``line:column``."""

        return f"{self.line}:{self.column}"
