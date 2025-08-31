#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from abc import ABC, abstractmethod
from dataclasses import dataclass

from erbsland.conf.source import Source, SourceIdentifier


@dataclass
class SourceResolverContext:
    """
    Context information for resolving an included source.

    :var include_text: The text from the include directive.
    :var source: Identifier of the source that contains the ``@include`` meta-command.
    """

    include_text: str
    source: SourceIdentifier


class SourceResolver(ABC):
    """Abstract interface for resolving include directives."""

    @abstractmethod
    def resolve(self, context: SourceResolverContext) -> list[Source]:
        """Resolve the sources referenced by an include directive.

        :param context: The context that describes the files to include.
        :returns: A list of resolved :class:`erbsland.conf.Source` objects.
        """
