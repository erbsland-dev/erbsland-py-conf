#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import datetime as dt
import re
from typing import Any, Callable, Type, TypeAlias, TypeVar, cast

from erbsland.conf.datetime import DateTime, Time
from erbsland.conf.time_delta import TimeDelta
from erbsland.conf.value_type import ValueType


ValueStorageType: TypeAlias = (
    str | int | float | bool | dt.date | DateTime | dt.datetime | Time | dt.time | TimeDelta | re.Pattern | bytes
)


def is_valid_storage_value(value: Any) -> bool:
    """Test if ``value`` uses a supported storage type."""

    return isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
            dt.date,
            DateTime,
            dt.datetime,
            Time,
            dt.time,
            TimeDelta,
            re.Pattern,
            bytes,
        ),
    )


_TYPE_MAP: dict[type, ValueType] = {
    str: ValueType.TEXT,
    int: ValueType.INTEGER,
    float: ValueType.FLOAT,
    bool: ValueType.BOOLEAN,
    dt.date: ValueType.DATE,
    Time: ValueType.TIME,
    dt.time: ValueType.TIME,
    DateTime: ValueType.DATE_TIME,
    dt.datetime: ValueType.DATE_TIME,
    TimeDelta: ValueType.TIME_DELTA,
    re.Pattern: ValueType.REGEX,
    bytes: ValueType.BYTES,
}


def value_type_from_storage_type(storage_type: Type) -> ValueType:
    """Translate a Python storage ``storage_type`` into a :class:`ValueType`."""

    if storage_type in _TYPE_MAP:
        return _TYPE_MAP[storage_type]
    raise ValueError(f"Unknown storage type {storage_type}")


def is_valid_storage_type(storage_type: Type) -> bool:
    """Test if ``storage_type`` is a supported storage type."""
    return storage_type in _TYPE_MAP


U = TypeVar("U")

_DEFAULT_FACTORIES: dict[type[Any], Callable[[], Any]] = {
    str: str,
    int: int,
    float: float,
    bool: lambda: False,
    dt.date: lambda: dt.date(1970, 1, 1),
    dt.datetime: lambda: dt.datetime(1970, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc),
    DateTime: lambda: DateTime(1970, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc),
    dt.time: dt.time(0, 0),
    Time: lambda: Time(0, 0),
    TimeDelta: lambda: TimeDelta(),
    re.Pattern: lambda: re.compile(""),
    bytes: bytes,
    list: lambda: [],
}


def default_for(expected_type: type[U]) -> U:
    """
    Return a default instance for ``expected_type``.

    :param expected_type: The type to create a default value for.
    :return: A new instance of ``expected_type`` using the registered factory.
    :raises TypeError: If the type has no registered default factory.
    """

    key: type[Any] = expected_type
    try:
        factory = _DEFAULT_FACTORIES[key]
    except KeyError:  # pragma: no cover
        raise TypeError(f"No default factory registered for {expected_type!r}") from None  # pragma: no cover
    return cast(U, factory())
