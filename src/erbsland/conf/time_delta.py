#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import enum

from dataclasses import dataclass


class TimeUnit(enum.Enum):
    """Supported units for :class:`TimeDelta` values."""

    NANOSECOND = "nanosecond"
    MICROSECOND = "microsecond"
    MILLISECOND = "millisecond"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# Mapping textual unit representations to :class:`TimeUnit` values.
TIME_DELTA_UNIT_MAP = {
    "ns": TimeUnit.NANOSECOND,
    "nanosecond": TimeUnit.NANOSECOND,
    "nanoseconds": TimeUnit.NANOSECOND,
    "us": TimeUnit.MICROSECOND,
    "µs": TimeUnit.MICROSECOND,
    "microsecond": TimeUnit.MICROSECOND,
    "microseconds": TimeUnit.MICROSECOND,
    # Milliseconds
    "ms": TimeUnit.MILLISECOND,
    "millisecond": TimeUnit.MILLISECOND,
    "milliseconds": TimeUnit.MILLISECOND,
    "s": TimeUnit.SECOND,
    "second": TimeUnit.SECOND,
    "seconds": TimeUnit.SECOND,
    "m": TimeUnit.MINUTE,
    "minute": TimeUnit.MINUTE,
    "minutes": TimeUnit.MINUTE,
    "h": TimeUnit.HOUR,
    "hour": TimeUnit.HOUR,
    "hours": TimeUnit.HOUR,
    "d": TimeUnit.DAY,
    "day": TimeUnit.DAY,
    "days": TimeUnit.DAY,
    "w": TimeUnit.WEEK,
    "week": TimeUnit.WEEK,
    "weeks": TimeUnit.WEEK,
    "month": TimeUnit.MONTH,
    "months": TimeUnit.MONTH,
    "year": TimeUnit.YEAR,
    "years": TimeUnit.YEAR,
}


@dataclass(frozen=True, slots=True)
class TimeDelta:
    """
    A time span consisting of a count and a unit.

    :var count: Numeric value of the span.
    :var unit: Unit associated with ``count``.
    """

    count: int = 0
    unit: TimeUnit = TimeUnit.SECOND

    def __str__(self) -> str:
        """Return a human-readable representation."""

        unit_text = self.unit.value
        if abs(self.count) != 1:
            unit_text += "s"
        return f"{self.count} {unit_text}"

    def to_test_text(self) -> str:
        """Return a machine-readable representation used in tests."""

        return f"{self.count},{self.unit.value}"
