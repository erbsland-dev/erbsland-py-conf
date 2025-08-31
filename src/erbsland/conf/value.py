#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from re import Pattern
from typing import Any, Iterator, TypeVar, Type

from erbsland.conf.impl.sentinels import MISSING, MissingType
from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.test_output import TestOutput
from erbsland.conf.time_delta import TimeDelta
from erbsland.conf.value_type import ValueType


T = TypeVar("T")

KeyType = str | int | Name | NamePath


class Value(ABC):
    """
    Represents a single value within a configuration document.

    .. _value_type_support:

    Supported Types for ``expected_type`` and ``value_type``
    --------------------------------------------------------

    The supported native value types you can use in various interfaces are:

    *   :class:`int`
    *   :class:`bool`
    *   :class:`float`
    *   :class:`str`
    *   :class:`bytes`
    *   :class:`datetime.date`
    *   :class:`datetime.time` or :class:`~erbsland.conf.Time`
    *   :class:`datetime.datetime` or :class:`~erbsland.conf.DateTime`
    *   :class:`datetime.timedelta` or :class:`~erbsland.conf.TimeDelta`
    *   :class:`re.Pattern`
    *   :class:`list` – only for :data:`~erbsland.conf.ValueType.VALUE_LIST` values.

    The type checking for all ``as_...`` and ``get_...`` methods that have a ``expected_type`` is strict;
    an integer is **not** implicitly converted to a float or string.

    For relaxed type conversion, use the :meth:`~erbsland.conf.Value.convert_to` method.

    .. _key_options:

    Options for the Parameter ``key``
    ---------------------------------

    For providing name-paths, you have the following options:

    :class:`str`
        You can provide a name-path in text format. This path is parsed and converted into
        a :class:`~erbsland.conf.NamePath` object.
    :class:`int`
        To address a value by index, you can provide an integer. This index works almost
        like using <code>value[index]</code>, except that a
        :class:`~erbsland.conf.ConfValueNotFound` is thrown instead of an
        :class:`IndexError`.
    :class:`~erbsland.conf.Name`
        Using a name is like using a name-path with a single element.
    :class:`~erbsland.conf.NamePath`
        By providing a name path object, you can address any value
        in the value tree, relative to the current value.

    .. _value_about_exceptions:

    About the Exceptions Raised by this API
    ---------------------------------------

    You can use a catch-all ``except Error:`` in your code to catch all exceptions raised by this API and
    output it as string to provide a user-friendly error message. The :class:`Error<erbsland.conf.Error>` class
    is the base class for all exceptions raised by this API. The following exception are thrown by the API:

    :class:`ConfSyntaxError<erbsland.conf.ConfSyntaxError>`
        If the string representation of a name path contains syntax errors.
    :class:`ConfValueNotFound<erbsland.conf.ConfValueNotFound>`
        If no value exists at the location of ``key`` and no default value is provided.
    :class:`ConfTypeMismatch<erbsland.conf.ConfTypeMismatch>`
        If the value at the given location does not match the expected value and no default value is provided.
    :class:`KeyError<builtins.KeyError>`
        The class :class:`ConfValueNotFound<erbsland.conf.ConfValueNotFound>` is also derived from
        :class:`KeyError<builtins.KeyError>`, to make value lookup compatible with other frameworks.
    :class:`Error<erbsland.conf.Error>`
        This is the base class for all exceptions raised by this API.

    .. _value_type_mapping:

    Native Values for Value Types
    -----------------------------

    The following table shows the native value types for each non-section/list value type:

    :data:`~erbsland.conf.ValueType.VALUE_INT`:
        :class:`int`
    :data:`~erbsland.conf.ValueType.VALUE_BOOL`:
        :class:`bool`
    :data:`~erbsland.conf.ValueType.VALUE_FLOAT`:
        :class:`float`
    :data:`~erbsland.conf.ValueType.VALUE_TEXT`:
        :class:`str`
    :data:`~erbsland.conf.ValueType.VALUE_BYTES`:
        :class:`bytes`
    :data:`~erbsland.conf.ValueType.VALUE_DATE`:
        :class:`datetime.date`
    :data:`~erbsland.conf.ValueType.VALUE_TIME`:
        :class:`~erbsland.conf.Time` (derived from :class:`datetime.time`)
    :data:`~erbsland.conf.ValueType.VALUE_DATETIME`:
        :class:`~erbsland.conf.DateTime` (derived from :class:`datetime.datetime`)
    :data:`~erbsland.conf.ValueType.VALUE_TIMEDELTA`:
        :class:`~erbsland.conf.TimeDelta`
    :data:`~erbsland.conf.ValueType.VALUE_REGEX`:
        :class:`re.Pattern`

    For every other value type, the native value is always ``None``.
    Please note: Value lists are *not* stored as native lists.

    """

    @property
    @abstractmethod
    def type(self) -> ValueType:
        """Return the type of this value."""

    @property
    @abstractmethod
    def name(self) -> Name | None:
        """Return the name of this value."""

    @property
    @abstractmethod
    def name_path(self) -> NamePath:
        """Return the full path to this value."""

    @property
    @abstractmethod
    def parent(self) -> Value | None:
        """Get the parent of this value, or None if this is the root value."""

    @property
    @abstractmethod
    def has_parent(self) -> bool:
        """Test if this value has a parent."""

    @property
    @abstractmethod
    def is_root(self) -> bool:
        """Test if this is the root value (i.e. the document)."""

    @property
    @abstractmethod
    def location(self) -> Location | None:
        """Get the location of this value."""

    @property
    @abstractmethod
    def native(self) -> Any | None:
        """
        Return the stored native data.

        :returns: The native values you can expect is described in :ref:`value_type_mapping`.
        """

    @abstractmethod
    def __getitem__(self, key: KeyType) -> Value:
        """
        Access a child value by name, name path, or index.

        :param key: The key used to access the child value. See :ref:`key_options` for details.
        :returns: The child value.
        :raises: See :ref:`value_about_exceptions`.
        """

    @abstractmethod
    def get(self, key: KeyType, default: Any = None) -> Value | Any:
        """
        Return a child value by name, name path, or index.

        :param key: The key used to access the child value. See :ref:`key_options` for details.
        :param default: Value to return when the child does not exist.
        :returns: The child value, or ``default`` if none is found.
        :raises: See :ref:`value_about_exceptions`.
        """

    @abstractmethod
    def __contains__(self, key: KeyType) -> bool:
        """
        Return ``True`` if a child value exists for ``key``.

        Accepted types for ``key`` are the same as for :meth:`__getitem__`.

        :param key: The key used to test for the child value. See :ref:`key_options` for details.
        :returns: ``True`` if a child value exists at ``key``.
        :raises: See :ref:`value_about_exceptions`.
        """

    @abstractmethod
    def __iter__(self) -> Iterator[Value]:
        """Iterate over the child values."""

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of child values."""

    @property
    @abstractmethod
    def first(self) -> Value:
        """
        Return the first child of this value.

        :raises ConfValueNotFound: If the value has no children.
        """

    @property
    @abstractmethod
    def last(self) -> Value:
        """
        Return the last child of this value.

        :raises ConfValueNotFound: If the value has no children.
        """

    @abstractmethod
    def as_type(self, expected_type: Type[T], *, default: T | None | MissingType = MISSING) -> T | None:
        """
        Convert the value to ``value_type`` if this value has the correct type.

        Type checking and conversion is strict; an integer is not implicitly converted to a float or string.

        :note: If you use ``list`` as type, you will get a unchecked value list as ``list[Value]``, and only
            if the value if of type ``ValueType.VALUE_LIST``. Please use the method :meth:`as_list` or `get_list`
            if you want to get a type checked list of values.

        :param expected_type: The type you expect and to convert the value to. See :ref:`value_type_support` for
            details about the supported types.
        :param default: The value returned if the conversion fails. If no default is provided,
            an exception is raised when the conversion fails.
        :returns: The converted value, or ``default`` if the conversion fails and if it is provided,
            if not, an exception is raised.
        :raises: See :ref:`value_about_exceptions`.
        """

    def as_int(self, *, default: int | None | MissingType = MISSING) -> int | None:
        """Shorthand for :meth:`as_type(int, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(int, default=default)

    def as_bool(self, *, default: bool | None | MissingType = MISSING) -> bool | None:
        """Shorthand for :meth:`as_type(bool, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(bool, default=default)

    def as_float(self, *, default: float | None | MissingType = MISSING) -> float | None:
        """Shorthand for :meth:`as_type(float, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(float, default=default)

    def as_text(self, *, default: str | None | MissingType = MISSING) -> str | None:
        """Shorthand for :meth:`as_type(str, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(str, default=default)

    def as_date(self, *, default: datetime.date | None | MissingType = MISSING) -> datetime.date | None:
        """Shorthand for :meth:`as_type(datetime.date, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(datetime.date, default=default)

    def as_time(self, *, default: datetime.time | None | MissingType = MISSING) -> datetime.time | None:
        """Shorthand for :meth:`as_type(datetime.time, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(datetime.time, default=default)

    def as_date_time(self, *, default: datetime.datetime | None | MissingType = MISSING) -> datetime.datetime | None:
        """Shorthand for :meth:`as_type(datetime.datetime, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(datetime.datetime, default=default)

    def as_bytes(self, *, default: bytes | None | MissingType = MISSING) -> bytes | None:
        """Shorthand for :meth:`as_type(bytes, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(bytes, default=default)

    def as_time_delta(self, *, default: TimeDelta | None | MissingType = MISSING) -> TimeDelta | None:
        """Shorthand for :meth:`as_type(TimeDelta, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(TimeDelta, default=default)

    def as_regex(self, *, default: Pattern[str] | None | MissingType = MISSING) -> Pattern[str] | None:
        """Shorthand for :meth:`as_type(Pattern, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(Pattern, default=default)

    def as_value_list(self, *, default: list | None | MissingType = MISSING) -> list | None:
        """Shorthand for :meth:`as_type(list, default)<erbsland.conf.Value.as_type>`."""
        return self.as_type(list, default=default)

    @abstractmethod
    def as_list(self, expected_type: Type[T], *, default: list[T] | None | MissingType = MISSING) -> list[T] | None:
        """
        Expect and return a list with elements of the type ``value_type``.

        This method first checks if it can build a list of elements with the expected type.
        If this is not possible, an exception is raised or, if provided, ``default`` is returned.

        :hint: We do not recommend using a default value for this method. If a single element in the list does
            not match the expected type, the default value will be returned, and it isn't clear for the user
            why the default was used. The exception will always contain the exact location and name path to
            the failed entry in the list.

        :important: This method will treat a single value as a list of one element.

        :param expected_type: The value type that is expected for all values in the returned list.
            See :ref:`value_type_support` for details.
        :param default: A default value to return if no list of elements can be built. If no default is provided,
            an exception is raised.
        :returns: A list with values of the expected type, or if a default is provided, the given ``default`` value.
        :raises: See :ref:`value_about_exceptions`.
        """

    @abstractmethod
    def to_test_text(self, output: TestOutput = TestOutput.DEFAULT) -> str:
        """Return the canonical string representation used in conformance tests."""

    @abstractmethod
    def to_test_value_tree(self, output: TestOutput = TestOutput.DEFAULT) -> str:
        """Return a graphical representation of the value tree."""

    @abstractmethod
    def get_type(self, key: KeyType, expected_type: Type[T], *, default: T | None | MissingType = MISSING) -> T | None:
        """
        Get a value by name, name path, or index and check if it is of the specified type.

        This method works like: ``self[key].as_type(value_type, default=default)``.
        See :meth:`as_type<erbsland.conf.value.Value.as_type>` for more details.

        :param key: The key used to access the child value. See :ref:`key_options` for details.
        :param expected_type: The type you expect and to convert the value to. See :ref:`value_type_support` for
            details about the supported types.
        :param default: The value returned if the conversion fails. If no default is provided,
            an exception is raised when the conversion fails.
        :returns: The converted value, or ``default`` if the conversion fails and if it is provided,
            if not, an exception is raised.
        :raises: See :ref:`value_about_exceptions`.
        """

    def get_int(self, key: KeyType, *, default: int | None | MissingType = MISSING) -> int | None:
        """Shorthand for :meth:`get_type(key, int, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, int, default=default)

    def get_bool(self, key: KeyType, *, default: bool | None | MissingType = MISSING) -> bool | None:
        """Shorthand for :meth:`get_type(key, bool, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, bool, default=default)

    def get_float(self, key: KeyType, *, default: float | None | MissingType = MISSING) -> float | None:
        """Shorthand for :meth:`get_type(key, float, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, float, default=default)

    def get_text(self, key: KeyType, *, default: str | None | MissingType = MISSING) -> str | None:
        """Shorthand for :meth:`get_type(key, str, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, str, default=default)

    def get_date(self, key: KeyType, *, default: datetime.date | None | MissingType = MISSING) -> datetime.date | None:
        """Shorthand for :meth:`get_type(key, datetime.date, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, datetime.date, default=default)

    def get_time(self, key: KeyType, *, default: datetime.time | None | MissingType = MISSING) -> datetime.time | None:
        """Shorthand for :meth:`get_type(key, datetime.time, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, datetime.time, default=default)

    def get_date_time(
        self, key: KeyType, *, default: datetime.datetime | None | MissingType = MISSING
    ) -> datetime.datetime | None:
        """Shorthand for :meth:`get_type(key, datetime.datetime, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, datetime.datetime, default=default)

    def get_bytes(self, key: KeyType, *, default: bytes | None | MissingType = MISSING) -> bytes | None:
        """Shorthand for :meth:`get_type(key, bytes, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, bytes, default=default)

    def get_time_delta(self, key: KeyType, *, default: TimeDelta | None | MissingType = MISSING) -> TimeDelta | None:
        """Shorthand for :meth:`get_type(key, TimeDelta, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, TimeDelta, default=default)

    def get_regex(self, key: KeyType, *, default: Pattern[str] | None | MissingType = MISSING) -> Pattern[str] | None:
        """Shorthand for :meth:`get_type(key, Pattern, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, Pattern, default=default)

    def get_value_list(self, key: KeyType, *, default: list | None | MissingType = MISSING) -> list | None:
        """Shorthand for :meth:`get_type(key, list, default)<erbsland.conf.Value.get_type>`."""
        return self.get_type(key, list, default=default)

    @abstractmethod
    def get_list(
        self, key: KeyType, expected_type: Type[T], *, default: list[T] | None | MissingType = MISSING
    ) -> list[T] | None:
        """
        Get and expect a list with elements of the type ``value_type``.

        This method works like `value[key].as_list(expected_type, default=default)`.
        See :meth:`as_list<erbsland.conf.Value.as_list>` for important details.

        :param key: The key used to access the child value. See :ref:`key_options` for details.
        :param expected_type: The value type that is expected for all values in the returned list.
            See :ref:`value_type_support` for details.
        :param default: A default value to return if no list of elements can be built. If no default is provided,
            an exception is raised.
        :returns: A list with values of the expected type, or if a default is provided, the given ``default`` value.
        :raises: See :ref:`value_about_exceptions`.
        """

    @abstractmethod
    def convert_to(self, value_type: Type[T]) -> T:
        """
        Best effort conversion to the specified type.

        If the conversion fails, a default value for the type is returned.

        :param value_type: The type you expect and to convert the value to. See :ref:`value_type_support` for
            details about the supported types.
        :return: You always get a value of the specified type.
        """

    @abstractmethod
    def __getstate__(self) -> dict[str, Any]:
        """Return a picklable state."""

    @abstractmethod
    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore from pickled state."""
