#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from erbsland.conf.source import SourceIdentifier


@dataclass(frozen=True, slots=True)
class AccessSources:
    """
    Identifiers for the target source and its lineage.

    :var source: Identifier of the source being checked.
    :var parent: Identifier of the parent source, or ``None`` if the source has no parent.
    :var root: Identifier of the root source.
    """

    source: SourceIdentifier
    parent: SourceIdentifier | None
    root: SourceIdentifier


class AccessCheckResult(Enum):
    """
    Result of an access check.
    """

    GRANTED = auto()
    """Tested source may be accessed."""
    DENIED = auto()
    """Tested source may not be accessed."""


class AccessCheck(ABC):
    """Interface for checking whether a source may be accessed."""

    @abstractmethod
    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        """
        Evaluate access for the given sources.

        In case of an error, the check can return :data:`~erbsland.conf.access_check.AccessCheckResult.DENIED` or
        simply raise a :class:`~erbsland.conf.error.ConfAccessError` exception, which is equivalent to
        :data:`AccessCheckResult.DENIED`.

        :param access_sources: Identifiers of the source to evaluate.
        :returns: The result of the access check.
        :raises Error: If the check fails due to an unexpected problem.
        """
