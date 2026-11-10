# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Relationships between explicitly configured values."""

from enum import StrEnum

from erbsland.conf.error import ConfValidationError


class DependencyMode(StrEnum):
    """The six ELCL dependency modes."""

    IF = "if"
    IF_NOT = "if_not"
    OR = "or"
    XOR = "xor"
    XNOR = "xnor"
    AND = "and"

    @classmethod
    def from_text(cls, value: str) -> "DependencyMode":
        """Parse a case-insensitive ELCL mode identifier."""
        if isinstance(value, str):
            try:
                return cls(value.lower().replace(" ", "_"))
            except ValueError:
                pass
        raise ConfValidationError("Unknown dependency mode")

    def accepts(self, source: bool, target: bool) -> bool:
        """Evaluate the two presence flags."""
        return {
            self.IF: not source or target,
            self.IF_NOT: not source or not target,
            self.OR: source or target,
            self.XOR: source != target,
            self.XNOR: source == target,
            self.AND: source and target,
        }[self]
