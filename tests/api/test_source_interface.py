#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from erbsland.conf.source import Source, SourceIdentifier


class CustomSource(Source):
    """Simple subclass used for exercising the Source interface."""

    def __init__(self, identifier: SourceIdentifier):
        self._identifier = identifier
        self._open = False

    def open(self) -> None:  # pragma: no cover - trivial
        self._open = True

    def is_open(self) -> bool:  # pragma: no cover - trivial
        return self._open

    def readline(self) -> str:  # pragma: no cover - trivial
        return ""

    def close(self) -> None:  # pragma: no cover - trivial
        self._open = False

    @property
    def identifier(self) -> SourceIdentifier:
        return self._identifier

    def start_digest_calculation(self):
        raise NotImplementedError()

    def get_digest(self) -> str:
        return ""


class TestCustomSource:
    """Tests for the Source methods using a subclass."""

    def test_repr(self):
        source = CustomSource(SourceIdentifier(SourceIdentifier.TEXT, "doc"))
        assert repr(source) == "Source(text:doc)"
