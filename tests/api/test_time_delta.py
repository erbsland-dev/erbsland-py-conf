#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import pytest

from erbsland.conf.time_delta import TimeDelta, TimeUnit


UNIT_NAMES = [
    (TimeUnit.NANOSECOND, "nanosecond"),
    (TimeUnit.MICROSECOND, "microsecond"),
    (TimeUnit.MILLISECOND, "millisecond"),
    (TimeUnit.SECOND, "second"),
    (TimeUnit.MINUTE, "minute"),
    (TimeUnit.HOUR, "hour"),
    (TimeUnit.DAY, "day"),
    (TimeUnit.WEEK, "week"),
    (TimeUnit.MONTH, "month"),
    (TimeUnit.YEAR, "year"),
]


class TestTimeDelta:
    @pytest.mark.parametrize("unit, name", UNIT_NAMES)
    def test_str_singular(self, unit, name):
        td = TimeDelta(1, unit)
        assert str(td) == f"1 {name}"

    @pytest.mark.parametrize("unit, name", UNIT_NAMES)
    def test_str_plural(self, unit, name):
        td = TimeDelta(2, unit)
        assert str(td) == f"2 {name}s"

    def test_str_negative_singular(self):
        td = TimeDelta(-1, TimeUnit.MINUTE)
        assert str(td) == "-1 minute"

    def test_str_negative_plural(self):
        td = TimeDelta(-2, TimeUnit.DAY)
        assert str(td) == "-2 days"

    def test_defaults(self):
        td = TimeDelta()
        assert td.count == 0
        assert td.unit is TimeUnit.SECOND

    @pytest.mark.parametrize("unit, name", UNIT_NAMES)
    def test_to_test_text(self, unit, name):
        td = TimeDelta(123, unit)
        assert td.to_test_text() == f"123,{name}"

    def test_to_test_text_negative(self):
        td = TimeDelta(-5, TimeUnit.HOUR)
        assert td.to_test_text() == "-5,hour"
