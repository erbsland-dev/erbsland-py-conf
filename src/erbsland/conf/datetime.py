#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import datetime as dt
import re


RE_TIME_FRACTIONS = re.compile(r"\.(\d+)")
RE_TIME_ZERO_OFFSET = re.compile(r"[+-]00:00$")


class Time(dt.time):
    """
    Represents a time of day with nanosecond precision.

    This class wraps :class:`datetime.time` to carry nanoseconds when needed. Any further operation on this class
    drops the nanosecond precision.
    """

    def __new__(
        cls,
        hour: int,
        minute: int,
        *,
        second: int = 0,
        microsecond: int = 0,
        nanosecond: int = 0,
        tzinfo=None,
        fold: int = 0,
    ):
        """
        Create a :class:`Time` instance.

        Only one of ``microsecond`` or ``nanosecond`` may be specified.

        :param hour: Hour component.
        :param minute: Minute component.
        :param second: Second component.
        :param microsecond: Microsecond component. Mutually exclusive with ``nanosecond``.
        :param nanosecond: Nanosecond component. Mutually exclusive with ``microsecond``.
        :param tzinfo: Time zone information.
        :param fold: Fold for times in a repeated interval.
        :raises ValueError: If both ``microsecond`` and ``nanosecond`` are specified.
        """
        if microsecond != 0 and nanosecond != 0:
            raise ValueError("Cannot specify both microsecond and nanosecond")
        if nanosecond != 0:
            self = super().__new__(cls, hour, minute, second, nanosecond // 1000, tzinfo, fold=fold)
            self._nanosecond = nanosecond
        else:
            self = super().__new__(cls, hour, minute, second, microsecond, tzinfo, fold=fold)
            self._nanosecond = microsecond * 1000
        return self

    @property
    def nanosecond(self) -> int:
        """Nanosecond component of the time."""
        return self._nanosecond

    @classmethod
    def fromisoformat(cls, time_string: str) -> "Time":
        result = dt.time.fromisoformat(time_string)
        if match := RE_TIME_FRACTIONS.search(time_string):
            if len(match.group(1)) > 6:
                fraction = match.group(1) + "0" * (9 - len(match.group(1)))
                nanoseconds = int(fraction)
                return cls(
                    result.hour, result.minute, second=result.second, nanosecond=nanoseconds, tzinfo=result.tzinfo
                )
        return cls(
            result.hour, result.minute, second=result.second, microsecond=result.microsecond, tzinfo=result.tzinfo
        )

    def elcl_format(self) -> str:
        """
        Return the time formatted for ELCL.

        The representation is based on ISO formatting with two changes:

        - Fractions use nanosecond precision.
        - An offset of ``+00:00`` is rendered as ``z``.
        """
        text = self.isoformat(timespec="microseconds" if self.nanosecond != 0 else "seconds")
        text = RE_TIME_FRACTIONS.sub(lambda m: f".{self.nanosecond:09d}".rstrip("0"), text)
        text = RE_TIME_ZERO_OFFSET.sub("z", text)
        return text

    @classmethod
    def patch_iso_time(cls, date_time_string: str) -> str:
        """
        Patch an ISO time string to conform to ELCL format.

        - Remove trailing zeros from fractions.
        - Render an offset of ``+00:00`` as ``z``.
        """
        date_time_string = RE_TIME_FRACTIONS.sub(lambda m: "." + m.group(1).rstrip("0"), date_time_string)
        date_time_string = RE_TIME_ZERO_OFFSET.sub("z", date_time_string)
        return date_time_string


class DateTime(dt.datetime):
    """
    Represents a combined date and time with nanosecond precision.

    This class wraps :class:`datetime.datetime` to carry nanoseconds when needed.
    Any operation on this class drops the nanosecond precision.
    """

    def __new__(
        cls,
        year: int,
        month: int,
        day: int,
        *,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        nanosecond: int = 0,
        tzinfo=None,
        fold: int = 0,
    ):
        """
        Create a :class:`DateTime` instance.

        Only one of ``microsecond`` or ``nanosecond`` may be specified.

        :param year: Year component.
        :param month: Month component.
        :param day: Day component.
        :param hour: Hour component.
        :param minute: Minute component.
        :param second: Second component.
        :param microsecond: Microsecond component. Mutually exclusive with ``nanosecond``.
        :param nanosecond: Nanosecond component. Mutually exclusive with ``microsecond``.
        :param tzinfo: Time zone information.
        :param fold: Fold for times in a repeated interval.
        :raises ValueError: If both ``microsecond`` and ``nanosecond`` are specified.
        """
        if microsecond != 0 and nanosecond != 0:
            raise ValueError("Cannot specify both microsecond and nanosecond")
        if nanosecond != 0:
            self = super().__new__(cls, year, month, day, hour, minute, second, nanosecond // 1000, tzinfo, fold=fold)
            self._nanosecond = nanosecond
        else:
            self = super().__new__(cls, year, month, day, hour, minute, second, microsecond, tzinfo, fold=fold)
            self._nanosecond = microsecond * 1000
        return self

    @property
    def nanosecond(self) -> int:
        """Nanosecond component of the date-time."""
        return self._nanosecond

    @classmethod
    def fromisoformat(cls, date_time_string: str) -> "DateTime":
        result = dt.datetime.fromisoformat(date_time_string)
        if match := RE_TIME_FRACTIONS.search(date_time_string):
            fraction = match.group(1) + "0" * (9 - len(match.group(1)))
            nanoseconds = int(fraction)
            return cls(
                result.year,
                result.month,
                result.day,
                hour=result.hour,
                minute=result.minute,
                second=result.second,
                nanosecond=nanoseconds,
                tzinfo=result.tzinfo,
            )
        return cls(
            result.year,
            result.month,
            result.day,
            hour=result.hour,
            minute=result.minute,
            second=result.second,
            microsecond=result.microsecond,
            tzinfo=result.tzinfo,
        )

    def elcl_format(self) -> str:
        """
        Return the date and time formatted for ELCL.

        The representation is based on ISO formatting with two changes:

        - Fractions use nanosecond precision.
        - An offset of ``+00:00`` is rendered as ``z``.
        """
        text = self.isoformat(sep=" ", timespec="microseconds" if self.nanosecond != 0 else "seconds")
        text = RE_TIME_FRACTIONS.sub(lambda m: f".{self.nanosecond:09d}".rstrip("0"), text)
        text = RE_TIME_ZERO_OFFSET.sub("z", text)
        return text.lower()

    @classmethod
    def patch_iso_time(cls, date_time_string: str) -> str:
        """
        Patch an ISO date-time string to conform to ELCL format.

        - Remove trailing zeros from fractions.
        - Render an offset of ``+00:00`` as ``z``.
        """
        date_time_string = RE_TIME_FRACTIONS.sub(lambda m: "." + m.group(1).rstrip("0"), date_time_string)
        date_time_string = RE_TIME_ZERO_OFFSET.sub("z", date_time_string)
        return date_time_string.lower()
