#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

# SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfInternalError, ConfSyntaxError
from erbsland.conf.parser import Parser
from erbsland.conf.source import Source
from erbsland.conf.source_resolver import SourceResolver, SourceResolverContext
from erbsland.conf.impl.parser_impl import MAX_INCLUDE_SOURCES
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.name_path import NamePath


class MappingResolver(SourceResolver):
    """Simple resolver that maps include texts to in-memory sources."""

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping
        self.calls: list[SourceResolverContext] = []

    def resolve(self, context: SourceResolverContext) -> list[Source]:
        self.calls.append(context)
        text = self.mapping.get(context.include_text)
        if text is None:
            return []
        return [TextSource(text)]


class RaisingResolver(SourceResolver):
    """Resolver that raises an unexpected exception."""

    def resolve(self, context: SourceResolverContext) -> list[Source]:
        raise ValueError("boom")


class DictResolver(SourceResolver):
    """Resolver that returns a dictionary instead of a list."""

    def resolve(self, context: SourceResolverContext):  # type: ignore[override]
        return {}


class MixedResolver(SourceResolver):
    """Resolver that returns a list containing a non-Source object."""

    def resolve(self, context: SourceResolverContext):  # type: ignore[override]
        return [TextSource("value = 1\n"), 1]


class TooManyResolver(SourceResolver):
    """Resolver that returns more sources than allowed."""

    def resolve(self, context: SourceResolverContext) -> list[Source]:
        return [TextSource("value = 1\n") for _ in range(MAX_INCLUDE_SOURCES + 1)]


class TestParserCustomResolver:
    def test_custom_resolver_is_used(self):
        resolver = MappingResolver({"extra": "[extra]\nvalue2 = 2\n"})
        parser = Parser()
        parser.resolver = resolver

        doc = parser.parse('[main]\nvalue1 = 1\n@include: "extra"\n')
        flat = doc.to_flat_dict()

        assert resolver.calls and resolver.calls[0].include_text == "extra"
        assert flat[NamePath.from_text("main.value1")].to_test_text() == "Integer(1)"
        assert flat[NamePath.from_text("extra.value2")].to_test_text() == "Integer(2)"

    @pytest.mark.parametrize(
        "resolver, expected_exc",
        [
            pytest.param(RaisingResolver(), ConfInternalError, id="unexpected-exception"),
            pytest.param(DictResolver(), ConfInternalError, id="not-a-list"),
            pytest.param(MixedResolver(), ConfInternalError, id="invalid-entry"),
        ],
    )
    def test_custom_resolver_invalid(self, resolver: SourceResolver, expected_exc: type[Exception]):
        parser = Parser()
        parser.resolver = resolver

        with pytest.raises(expected_exc):
            parser.parse('@include: "extra"\n')

    def test_custom_resolver_too_many_sources(self):
        parser = Parser()
        parser.resolver = TooManyResolver()

        with pytest.raises(ConfSyntaxError):
            parser.parse('@include: "extra"\n')
