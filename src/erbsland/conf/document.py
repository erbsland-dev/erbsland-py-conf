#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from abc import abstractmethod

from erbsland.conf.impl.value_storage_type import (
    ValueStorageType,
)
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.value import Value

ValidValueToAdd = ValueStorageType | list[ValueStorageType] | list[list[ValueStorageType]]
NamePathLike = str | NamePath | Name


class Document(Value):
    """A hierarchical configuration document."""

    @abstractmethod
    def to_flat_dict(self) -> dict[NamePath, Value]:
        """Return all values in a flat mapping keyed by their full name paths."""


class DocumentBuilder:
    """Utility for incrementally building configuration documents."""

    def __init__(self):
        from erbsland.conf.impl.document_impl import DocumentBuilderImpl

        self._impl = DocumentBuilderImpl()

    def reset(self):
        """Clear all previously added values and the current document."""
        self._impl.reset()

    def get_document_and_reset(self) -> Document:
        """Return the current document and reset the builder."""
        return self._impl.get_document_and_reset()

    def add_section_map(self, name_path: NamePathLike):
        """
        Create a new section map at ``name_path``.

        Intermediate sections are created as needed, and existing intermediate sections are converted to maps.
        The builder performs name-collision and syntax checks to ensure that only valid documents are produced.

        :param name_path: Name path of the section to add.
        """
        self._impl.add_section_map(name_path, None)

    def add_section_list(self, name_path: NamePathLike):
        """
        Add a new entry to a section list at ``name_path``.

        Intermediate sections are created as needed. If a section list already exists at the given path, the new
        entry is appended to it; otherwise a new section list with a single entry is created. The builder performs
        name-collision and syntax checks to ensure validity.

        :param name_path: Name path of the section.
        """
        self._impl.add_section_list(name_path, None)

    def add_value(self, name_path: NamePathLike, value: ValidValueToAdd):
        """
        Add a value to the document.

        Values can be added only to existing sections. If ``name_path`` is a :class:`Name` or a single-element
        :class:`NamePath`, the value is added to the most recently created section.

        The builder performs name-collision and syntax checks to ensure that only
        valid documents are produced.

        :note: Adding meta-values is not supported.

        :param name_path: Name path of the value. A single name adds the value to the last section created
            with this builder.
        :param value: The native value to add. Supported types are ``str``, ``int``, ``float``, ``bool``, ``datetime``,
            ``date``, ``time``, ``timedelta`` and ``bytes``. Use a ``list`` to add a list of values,
            or a nested ``list`` to add a value matrix.
        """
        self._impl.add_native_value(name_path, value)
