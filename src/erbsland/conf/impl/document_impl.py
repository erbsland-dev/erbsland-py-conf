#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from typing import Tuple

from erbsland.conf.document import Document, ValidValueToAdd
from erbsland.conf.error import ConfNameConflict
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.impl.value_storage_type import (
    ValueStorageType,
    is_valid_storage_value,
    value_type_from_storage_type,
)
from erbsland.conf.location import Location
from erbsland.conf.name import Name, NameType
from erbsland.conf.name_path import NamePath
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType


NamePathLike = str | NamePath | Name


def validate_name_path_like(name_path: NamePathLike) -> NamePath:
    """Validate and convert *name_path* to a :class:`NamePath` instance."""

    if name_path is None:
        raise ValueError("The name path must not be None")
    if not isinstance(name_path, (str, Name, NamePath)):
        raise ValueError("Invalid name path type. Must be 'str', 'Name' or 'NamePath'")
    if isinstance(name_path, str):
        name_path = NamePath.from_text(name_path)
    elif isinstance(name_path, Name):
        name_path = NamePath([name_path])
    if len(name_path) == 0:
        raise ValueError("The name path must not be empty")
    for name in name_path:
        if name.type in (NameType.INDEX, NameType.TEXT_INDEX):
            raise ValueError("The name path must not contain an index")
    return name_path


def validate_value_to_add(value: ValidValueToAdd):
    """Ensure that *value* can be added to a document."""

    if value is None:
        raise ValueError("Cannot add None to a document")
    if isinstance(value, list):
        if len(value) == 0:
            raise ValueError("Cannot add empty list to a document")
        if isinstance(value[0], ValueStorageType):
            for index, v in enumerate(value):
                if not is_valid_storage_value(v):
                    raise ValueError(f"Value at [{index}] has an unsupported type: {type(v)}")
        if isinstance(value[0], list):
            for index, v in enumerate(value):
                if not isinstance(v, list):
                    raise ValueError(f"Value at [{index}] is not a list")
                for index2, v2 in enumerate(v):
                    if not is_valid_storage_value(v2):
                        raise ValueError(f"Value at [{index}][{index2}] has an unsupported type: {type(v2)}")
    if not is_valid_storage_value(value):
        raise ValueError(f"Unsupported value type to add: {type(value)}")


def create_value_object(value: ValidValueToAdd, name_path: NamePathLike) -> ValueImpl:
    """Create a :class:`ValueImpl` from a native Python value."""

    name = name_path[-1]
    if isinstance(value, list):
        new_value = ValueImpl(ValueType.VALUE_LIST, name)
        for index, v in enumerate(value):
            new_value.add_child(create_value_object(v, Name.create_index(index)))
        return new_value
    value_type = value_type_from_storage_type(type(value))
    return ValueImpl(value_type, name, value)


class DocumentImpl(ValueImpl, Document):
    """Concrete :class:`Document` backed by :class:`ValueImpl` nodes."""

    def __init__(self):
        """Initialize an empty document."""

        super().__init__(ValueType.DOCUMENT, None)

    def to_flat_dict(self) -> dict[NamePath, Value]:
        """Return all values in the document as a flat dictionary keyed by name paths."""

        result: dict[NamePath, Value] = {}
        stack: list[ValueImpl] = [self]
        while stack:
            current_node = stack.pop()
            if not current_node.is_root:
                result[current_node.name_path] = current_node
            for child in reversed(current_node._children):
                stack.append(child)
        return result


class DocumentBuilderImpl:
    """Mutable builder used by the parser to construct a document."""

    def __init__(self, document_location: Location | None = None):
        """Create a new builder with an empty document."""

        self._document = DocumentImpl()
        if document_location is not None:
            self._document.location = document_location
        self._last_section: ValueImpl | None = None

    @property
    def last_section(self) -> ValueImpl | None:
        """Return the last section added to the document."""
        return self._last_section

    def reset(self):
        """Reset the builder to an empty state."""

        self._document = DocumentImpl()
        self._last_section = None

    def add_section_map(self, name_path: NamePathLike, assignment_location: Location | None):
        """Add a map section to the document."""

        name_path = validate_name_path_like(name_path)
        existing_map = self._document.get(name_path)
        if existing_map is not None:
            if existing_map.type == ValueType.INTERMEDIATE_SECTION:
                existing_map.type = ValueType.SECTION_WITH_NAMES
                self._last_section = existing_map
                return
            if existing_map.type == ValueType.SECTION_WITH_TEXTS:
                raise ConfNameConflict(
                    "A section with text names cannot be converted back to a section with regular names.",
                    source=assignment_location,
                    name_path=name_path,
                )
            else:
                raise ConfNameConflict(
                    "The value or section with this name was defined before.",
                    source=assignment_location,
                    name_path=name_path,
                )
        parent = self._get_or_create_parent_for_section(name_path, assignment_location)
        parent.add_child(ValueImpl(ValueType.SECTION_WITH_NAMES, name_path[-1], location=assignment_location))
        self._last_section = parent

    def add_section_list(self, name_path: NamePathLike, assignment_location: Location | None):
        """Add a list section to the document."""

        name_path = validate_name_path_like(name_path)
        if name_path[-1].is_text():
            raise ConfNameConflict(
                "A section list cannot have a text name.",
                source=assignment_location,
                name_path=name_path,
            )
        existing_list = self._document.get(name_path)
        if existing_list is not None:
            if existing_list.type == ValueType.SECTION_LIST:
                next_index = len(existing_list)
                new_value = ValueImpl(
                    ValueType.SECTION_WITH_NAMES, Name.create_index(next_index), location=assignment_location
                )
                existing_list.add_child(new_value)
                self._last_section = new_value
                return
            else:
                raise ConfNameConflict(
                    "The name of the list section was defined before as a different type.",
                    source=assignment_location,
                    name_path=name_path,
                )
        parent = self._get_or_create_parent_for_section(name_path, assignment_location)
        new_value = ValueImpl(ValueType.SECTION_LIST, name_path[-1], location=assignment_location)
        first_entry = ValueImpl(ValueType.SECTION_WITH_NAMES, Name.create_index(0), location=assignment_location)
        new_value.add_child(first_entry)
        parent.add_child(new_value)
        self._last_section = first_entry

    def add_native_value(self, name_path: NamePathLike, value: ValidValueToAdd):
        """Add a native Python value to the document."""

        name_path = validate_name_path_like(name_path)
        validate_value_to_add(value)
        value = create_value_object(value, name_path)
        self.add_value(name_path, value, None)

    def add_value(self, name_path: NamePathLike, value: ValueImpl, assignment_location: Location | None):
        """Add a pre-built :class:`ValueImpl` to the document."""

        name_path = validate_name_path_like(name_path)
        assert name_path[-1] == value.name
        if len(name_path) == 1:
            parent = self._last_section
            if parent is None:
                raise ConfNameConflict(
                    "Cannot add a value to a document without a section.",
                    source=assignment_location,
                    name_path=name_path,
                )
        else:
            parent = self._resolve_existing_section(name_path, assignment_location)
            if not parent.type.is_map() or parent.type == ValueType.INTERMEDIATE_SECTION:
                raise ConfNameConflict(
                    "A partial name-path to this value is not a section.",
                    source=assignment_location,
                    name_path=name_path,
                )
        if parent.has_child(name_path[-1]):
            raise ConfNameConflict(
                "A value with this name was defined before.",
                source=assignment_location,
                name_path=name_path,
            )
        parent.add_child(value)

    def get_document_and_reset(self) -> DocumentImpl:
        """Return the built document and reset the builder."""

        doc = self._document
        self.reset()
        return doc

    # --- helper methods -------------------------------------------------

    def _resolve_existing_section(self, name_path: NamePath, assignment_location: Location | None) -> ValueImpl:
        """
        Return the section for *name_path*, resolving section lists.

        Raises :class:`ConfNameConflict` if the section does not exist.
        """

        current = self._document
        current_path = NamePath()
        for name in name_path[:-1]:
            current_path.append(name)
            next_value = current.get(name)
            if next_value is None:
                raise ConfNameConflict(
                    f"There is no section at {current_path}.",
                    source=assignment_location,
                    name_path=name_path,
                )
            if next_value.type == ValueType.SECTION_LIST:
                current = next_value[-1]
            elif next_value.type.is_map():
                current = next_value
            else:
                raise ConfNameConflict(
                    f"The name-path to this value is no section.",
                    source=assignment_location,
                    name_path=name_path,
                )
        return current

    def _get_or_create_parent_for_section(self, name_path: NamePath, assignment_location: Location | None) -> ValueImpl:
        """Return the parent section for *name_path*, creating intermediate sections as needed."""

        current = self._document
        add_value_for_rollback: Tuple[ValueImpl, ValueImpl] | None = None
        try:
            for name in name_path[:-1]:
                if name.type in [NameType.INDEX, NameType.TEXT_INDEX]:
                    raise ConfNameConflict(
                        "Indexes are not allowed in section name-paths.",
                        source=assignment_location,
                        name_path=name_path,
                    )
                if name.type == NameType.TEXT:
                    raise ConfNameConflict(
                        "Sections with text-names must not have sub-sections.",
                        source=assignment_location,
                        name_path=name_path,
                    )
                next_value = current.get(name)
                if next_value is None:
                    next_value = ValueImpl(ValueType.INTERMEDIATE_SECTION, name, location=assignment_location)
                    if add_value_for_rollback is None:
                        add_value_for_rollback = (current, next_value)  # Remember this operation for rollback
                    current.add_child(next_value)
                elif next_value.type == ValueType.SECTION_LIST:
                    next_value = next_value[-1]  # For a section list, use the last element.
                elif not next_value.type.is_map():
                    raise ConfNameConflict(
                        f"The name-path of the section conflicts with {next_value.name_path}.",
                        source=assignment_location,
                        name_path=name_path,
                    )
                current = next_value
            return current
        except ConfNameConflict:
            # Make sure the document tree stays unchanged on error.
            if add_value_for_rollback is not None:
                add_value_for_rollback[0].remove_child(add_value_for_rollback[1].name)
            raise
