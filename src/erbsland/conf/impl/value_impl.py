#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import datetime
import re
import weakref
from typing import Any, Iterator, Type, cast, NoReturn

from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.error import ConfNameConflict, ConfValueNotFound, ConfTypeMismatch, Error
from erbsland.conf.impl.sentinels import MissingType, MISSING
from erbsland.conf.impl.text_escape import escape_text, escape_text_for_test
from erbsland.conf.impl.value_storage_type import (
    ValueStorageType,
    is_valid_storage_value,
    value_type_from_storage_type,
    is_valid_storage_type,
    default_for,
)
from erbsland.conf.impl.value_tree_helper import ValueTreeHelper
from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.test_output import TestOutput
from erbsland.conf.value import Value, T, KeyType
from erbsland.conf.value_type import ValueType


def _name_path_from_key(key: str | Name | NamePath) -> NamePath:
    """Normalize various key types to a :class:`NamePath` instance."""

    if isinstance(key, NamePath):
        return key
    if isinstance(key, Name):
        return NamePath(key)
    if isinstance(key, str):
        return NamePath.from_text(key)
    raise TypeError(f"Unsupported key type: {type(key)}")  # pragma: no cover


class ValueImpl(Value):
    """Internal representation of a document node."""

    __slots__ = ("_type", "_name", "_data", "_parent", "_children", "_children_by_name", "_location")

    def __init__(
        self, value_type: ValueType, name: Name | None, data: ValueStorageType = None, location: Location | None = None
    ):
        """
        Create a new value node.

        :param value_type: The type of the value represented by this node.
        :param name: The name of the value, or ``None`` for the document root.
        :param data: Optional primitive data associated with the value.
        :param location: Location information within the source document.
        """

        if not isinstance(value_type, ValueType):
            raise ValueError(f"'value_type' must be a ValueType")
        if name is None:
            if value_type is not ValueType.DOCUMENT:
                raise ValueError("'name' must be set for non-root values")
        elif not isinstance(name, Name):
            raise ValueError(f"'name' must be a Name, not {type(name)}")
        if data is not None and not is_valid_storage_value(data):
            raise ValueError(f"Invalid type for value: {type(data)}")
        if location is not None and not isinstance(location, Location):
            raise ValueError(f"'location' must be a Location, not {type(location)}")
        self._type: ValueType = value_type
        self._name: Name | None = name
        self._data: ValueStorageType | None = data
        self._parent: weakref.ReferenceType[ValueImpl] | None = None
        self._children: list[ValueImpl] = []
        self._children_by_name: dict[Name, ValueImpl] = {}
        self._location: Location | None = location

    @classmethod
    def from_data(cls, name: Name, data: ValueStorageType, location: Location | None = None):
        """
        Construct a value from *name* and *data*.

        :param name: The name of the value.
        :param data: The value data to drive the value type from.
        :param location: Location information within the source document.
        """

        if not isinstance(name, Name):
            raise ValueError(f"'name' must be a Name, not {type(name)}")
        if data is not None and not is_valid_storage_value(data):
            raise ValueError(f"Invalid type for value: {type(data)}")
        if location is not None and not isinstance(location, Location):
            raise ValueError(f"'location' must be a Location, not {type(location)}")
        return cls(value_type_from_storage_type(type(data)), name, data, location)

    @property
    def type(self) -> ValueType:
        return self._type

    @type.setter
    def type(self, value_type: ValueType):
        # There are two valid changes to the value type:
        assert (
            self._type == ValueType.INTERMEDIATE_SECTION
            and value_type in (ValueType.SECTION_WITH_NAMES, ValueType.SECTION_WITH_TEXTS)
        ) or (self._type == ValueType.SECTION_WITH_NAMES and value_type == ValueType.SECTION_WITH_TEXTS)
        self._type = value_type

    @property
    def name(self) -> Name | None:
        return self._name

    @name.setter
    def name(self, name: Name):
        assert isinstance(name, Name)
        self._name = name

    @property
    def name_path(self) -> NamePath:
        path_parts = []
        current = self
        while current is not None and current.name is not None:
            path_parts.insert(0, current.name)
            current = current.parent
        return NamePath(path_parts)

    @property
    def parent(self) -> Value | None:
        return self._parent() if self._parent else None

    @property
    def has_parent(self) -> bool:
        return self._parent is not None

    @property
    def is_root(self) -> bool:
        return self._type is ValueType.DOCUMENT and self._parent is None

    @property
    def location(self) -> Location | None:
        return self._location

    @location.setter
    def location(self, location: Location):
        """Set location information for this value."""

        self._location = location

    @property
    def native(self) -> ValueStorageType:
        return self._data

    def has_child(self, name: Name) -> bool:
        """Return ``True`` if a child with *name* exists."""

        return name in self._children_by_name

    def add_child(self, value: ValueImpl) -> None:
        """
        Add *value* as a child of this value and validate if adding this value results in a valid configuration.

        The method enforces the structural rules of the configuration language and raises :class:`ConfNameConflict`
        if the combination is not permitted.

        :param value: The value to add as a child.
        """

        if value.has_parent:
            raise ValueError("Cannot add child to a value that already has a parent")
        if value.name is None:
            raise ValueError("Cannot add a child without a name to a parent value")
        if self.type == ValueType.SECTION_WITH_TEXTS:
            if value.name.is_regular():
                raise ConfNameConflict(f"Cannot mix values with regular and text names in the same section")
        elif self.type in (ValueType.SECTION_WITH_NAMES, ValueType.DOCUMENT):
            if value.name.is_text():
                if len(self._children) > 0:
                    raise ConfNameConflict(f"Cannot mix values with text and regular names in the same section")
                self.type = ValueType.SECTION_WITH_TEXTS  # Change the section type.
        elif self.type in (ValueType.SECTION_LIST, ValueType.VALUE_LIST):
            if not value.name.is_index():
                raise ConfNameConflict(f"Values in a value or section list must have an index name")
        elif self.type is ValueType.INTERMEDIATE_SECTION:
            if not value.type.is_section():
                raise ConfNameConflict(f"You must not add a value to an intermediate section")
            if value.name.is_text():
                if len(self._children) > 0:
                    raise ConfNameConflict(f"Cannot mix sub sections with text and regular names in the same section")
                self.type = ValueType.SECTION_WITH_TEXTS
        else:
            raise ConfNameConflict(f"Cannot add a child to a value of type {self.type.value}")
        value._parent = weakref.ref(self)
        self._children.append(value)
        self._children_by_name[value.name] = value

    def remove_child(self, name: Name) -> None:
        """Remove the child with the given *name*."""

        child = self._children_by_name.pop(name)
        assert child is not None
        self._children.remove(child)
        child._parent = None

    # --- Display helpers ---

    def __str__(self) -> str:
        if self._type.is_single_value():
            if self._type is ValueType.TEXT:
                value_str = '"' + escape_text(self._data) + '"'
            else:
                value_str = str(self._data)
            return f"{self._type.value}(name={self._name}, data={value_str})"
        else:
            return f"{self._type.value}(name={self._name}, size={len(self._children)})"

    # --- Child access helpers ---

    def _child_for_name(self, name: Name) -> ValueImpl | None:
        assert isinstance(name, Name)
        if not self._type.is_container():
            return None
        if name.is_index() or name.is_text_index():
            if not self._type.is_list():
                return None
            index = name.as_index()
            if 0 <= index < len(self._children):
                return self._children[index]
            return None
        if self._type == ValueType.SECTION_LIST:
            assert self._children
            return self._children[-1]._children_by_name.get(name)
        if not self._type.is_map():
            return None
        return self._children_by_name.get(name)

    def __getitem__(self, key: str | int | Name | NamePath) -> Value:
        if isinstance(key, int):
            try:
                return self._children[key]
            except IndexError:
                name_path = NamePath(Name.create_index(key))
                raise ConfValueNotFound("Value not found", name_path=name_path)
        current: ValueImpl = self
        name_path = _name_path_from_key(key)
        for name in name_path:
            child = current._child_for_name(name)
            if child is None:
                raise ConfValueNotFound("Value not found", name_path=name_path)
            current = child
        return current

    def get(self, key: str | int | Name | NamePath, default: Any = None) -> Value | Any:
        try:
            return self[key]
        except ConfValueNotFound:
            return default

    def __contains__(self, key: str | int | Name | NamePath) -> bool:
        try:
            self.__getitem__(key)
            return True
        except ConfValueNotFound:
            return False

    def __iter__(self) -> Iterator[Value]:
        return iter(self._children)

    def __len__(self) -> int:
        return len(self._children)

    @property
    def first(self) -> Value:
        try:
            return self._children[0]
        except IndexError as error:
            raise ConfValueNotFound("There is no first value", name_path=self.name_path) from error

    @property
    def last(self) -> Value:
        try:
            return self._children[-1]
        except IndexError as error:
            raise ConfValueNotFound("There is no last value", name_path=self.name_path) from error

    # --- Type conversion helpers ---

    @staticmethod
    def _type_from_expected_type_param(expected_type: Type[T]) -> ValueType:
        if expected_type is list:
            return ValueType.VALUE_LIST
        elif is_valid_storage_type(expected_type):
            return value_type_from_storage_type(expected_type)
        else:
            raise ValueError(f"Unsupported type: {type(expected_type)}")

    @staticmethod
    def _raise_type_mismatch(value: ValueImpl, expected_type: ValueType, actual_type: ValueType) -> NoReturn:
        raise ConfTypeMismatch(
            f"Expected value of type {expected_type.value}, got {actual_type.value}",
            source=value.location,
            name_path=value.name_path,
        )

    def as_type(self, expected_type: Type[T], default: T | None | MissingType = MISSING) -> T | None:
        expected_value_type = self._type_from_expected_type_param(expected_type)
        if self._type == expected_value_type:
            if expected_value_type == ValueType.VALUE_LIST:
                return self._children.copy()
            else:
                return self._data
        if default is not MISSING:
            return cast(T, default)
        self._raise_type_mismatch(self, expected_value_type, self._type)

    def as_list(self, expected_type: Type[T], default: list[T] | None | MissingType = MISSING) -> list[T] | None:
        expected_value_type = self._type_from_expected_type_param(expected_type)
        if expected_value_type == ValueType.VALUE_LIST:
            raise ValueError(f"Nested lists are not supported by this method")
        if self._type == expected_value_type:
            return [self._data]
        if self._type == ValueType.VALUE_LIST:
            result = []
            for child in self._children:
                if child._type != expected_value_type:
                    if default is not MISSING:
                        return cast(list[T], default)
                    raise ConfTypeMismatch(
                        f"Expected a list of {expected_value_type.value}, but found {child._type.value}",
                        source=child.location,
                        name_path=child.name_path,
                    )
                result.append(child._data)
            return result
        if default is not MISSING:
            return cast(list[T], default)
        raise ConfTypeMismatch(
            f"Expected a single value or a list of {expected_value_type.value}, but got {self._type.value}",
            source=self.location,
            name_path=self.name_path,
        )

    def _test_text_content(self, output: TestOutput) -> str:
        """Convert the value to a string for use in conformance tests."""
        match self._type:
            case ValueType.INTEGER:
                return str(self._data)
            case ValueType.BOOLEAN:
                return "true" if self._data else "false"
            case ValueType.FLOAT:
                return f"{self._data:.17g}".lower()
            case ValueType.TEXT:
                if output & TestOutput.MINIMAL_ESC:
                    return '"' + escape_text(self._data) + '"'
                return '"' + escape_text_for_test(self._data) + '"'
            case ValueType.DATE:
                return self._data.isoformat()
            case ValueType.TIME:
                if isinstance(self._data, Time):
                    return self._data.elcl_format()
                return Time.patch_iso_time(self._data.isoformat())  # pragma: no cover
            case ValueType.DATE_TIME:
                if isinstance(self._data, DateTime):
                    return self._data.elcl_format()
                return DateTime.patch_iso_time(self._data.isoformat())  # pragma: no cover
            case ValueType.BYTES:
                return str(self._data.hex()).lower()
            case ValueType.TIME_DELTA:
                return self._data.to_test_text()
            case ValueType.REGEX:
                if output & TestOutput.MINIMAL_ESC:
                    return '"' + escape_text(self._data.pattern) + '"'
                return '"' + escape_text_for_test(self._data.pattern) + '"'
            case t if t.is_container():
                if output & TestOutput.CONTAINER_SIZE:
                    return f"size={len(self._children)}"
                return ""
            case _:
                return ""

    def to_test_text(self, output: TestOutput = TestOutput.DEFAULT) -> str:
        """Convert the value to a string for use in conformance tests."""
        return f"{self._type.value}({self._test_text_content(output)})"

    def to_test_value_tree(self, output: TestOutput = TestOutput.DEFAULT) -> str:
        helper = ValueTreeHelper(self, output)
        return "\n".join(helper.render())

    def get_type(
        self, key: str | int | Name | NamePath, expected_type: Type[T], *, default: T | None | MissingType = MISSING
    ) -> T | None:
        expected_value_type = self._type_from_expected_type_param(expected_type)
        try:
            value = cast(ValueImpl, self.__getitem__(key))
            assert isinstance(value, ValueImpl)
        except ConfValueNotFound:
            if default is not MISSING:
                return cast(T, default)
            raise
        if value.type == expected_value_type:
            if expected_value_type == ValueType.VALUE_LIST:
                return value._children.copy()
            return value._data
        if default is not MISSING:
            return cast(T, default)
        self._raise_type_mismatch(value, expected_value_type, value.type)

    def convert_to(self, value_type: Type[T]) -> T:
        expected_value_type = self._type_from_expected_type_param(value_type)
        if self._type == expected_value_type:
            if expected_value_type == ValueType.VALUE_LIST:
                return self._children.copy()
            return self._data
        try:
            match expected_value_type:
                case ValueType.INTEGER:
                    return int(self._data)
                case ValueType.BOOLEAN:
                    return bool(self._data)
                case ValueType.FLOAT:
                    return float(self._data)
                case ValueType.TEXT:
                    return str(self._data)
                case ValueType.DATE:
                    if self._type == ValueType.DATE_TIME:
                        return self._data.date()
                    elif self._type == ValueType.TEXT:
                        return datetime.date.fromisoformat(self._data)
                case ValueType.TIME:
                    if self._type == ValueType.DATE_TIME:
                        return self._data.time()
                    elif self._type == ValueType.TEXT:
                        return Time.fromisoformat(self._data)
                case ValueType.DATE_TIME:
                    if self._type == ValueType.TEXT:
                        return DateTime.fromisoformat(self._data)
                case ValueType.BYTES:
                    return str(self._data).encode("utf-8")
                case ValueType.TIME_DELTA:
                    pass
                case ValueType.REGEX:
                    return re.compile(re.escape(str(self._data)))
                case ValueType.VALUE_LIST:
                    if self._type.is_single_value():
                        return self
                    if self._children:
                        return self._children.copy()
                case _:  # pragma: no cover
                    pass  # pragma: no cover
        except (ValueError, re.error):  # re.error for Python < 3.13
            return default_for(value_type)

    def get_list(
        self, key: KeyType, expected_type: Type[T], default: list[T] | None | MissingType = MISSING
    ) -> list[T] | None:
        return self[key].as_list(expected_type, default=default)

    def __getstate__(self) -> dict[str, Any]:
        return {
            "_v": 1,
            "type": self._type,
            "name": self._name,
            "data": self._data,
            "children": self._children,
            "location": self._location,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        if state["_v"] != 1:
            raise ValueError(f"Unsupported version: {state['_v']}")
        self._type = state["type"]
        self._name = state["name"]
        self._data = state["data"]
        self._children = state["children"]
        self._location = state["location"]
        self._children_by_name = {}
        for child in self._children:
            child._parent = weakref.ref(self)
            self._children_by_name[child.name] = child
