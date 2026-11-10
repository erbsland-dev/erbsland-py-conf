# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Reusable compiled validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erbsland.conf.document import Document
from erbsland.conf.value import Value
from .rule import Rule


@dataclass(frozen=True, slots=True)
class Rules:
    """An immutable schema. Each validation has its own indexes and traversal state."""

    _root: Rule

    @property
    def root(self) -> Rule:
        """Read-only root rule metadata."""
        return self._root

    @classmethod
    def from_document(cls, document: Document) -> Rules:
        """Compile a parsed rules document, raising ConfValidationError for invalid definitions."""
        from erbsland.conf.impl.vr.loader import Loader
        from erbsland.conf.impl.vr.compiler import compile_rules

        return cls(compile_rules(Loader(document).load()))

    @classmethod
    def loads(cls, text: str) -> Rules:
        """Parse and compile rules from ELCL text using the standard parser."""
        from erbsland.conf.parser import loads

        return cls.from_document(loads(text))

    @classmethod
    def load(cls, path: str | Path) -> Rules:
        """Parse and compile an ELCL rules file using the standard parser."""
        from erbsland.conf.parser import load

        return cls.from_document(load(path))

    def validate(self, value: Value, version: int) -> None:
        """Validate a document or section in place.

        Insert defaults and attach metadata. The version must be a nonnegative
        integer. Raise ConfValidationError on the first failure; partial updates
        are possible on failure. Revalidation refreshes defaults and metadata
        only inside the supplied subtree.
        """
        from erbsland.conf.impl.vr.validator import Validator

        Validator(self._root, value, version).validate()
