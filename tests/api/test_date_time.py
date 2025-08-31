#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime as dt
import pytest

from erbsland.conf.datetime import DateTime, Time


class TestDateTimeWrapper:
    def test_conflicting_micro_and_nanoseconds(self):
        with pytest.raises(ValueError, match="Cannot specify both microsecond and nanosecond"):
            DateTime(2024, 1, 2, microsecond=1, nanosecond=1)

    def test_new_with_microsecond(self):
        value = DateTime(2024, 1, 2, hour=3, minute=4, second=5, microsecond=456, tzinfo=dt.timezone.utc)
        assert value.nanosecond == 456000
        assert value.elcl_format() == "2024-01-02 03:04:05.000456z"

    def test_new_with_nanosecond(self):
        value = DateTime(2024, 1, 2, hour=3, minute=4, second=5, nanosecond=789123456, tzinfo=dt.timezone.utc)
        assert value.nanosecond == 789123456
        assert value.elcl_format() == "2024-01-02 03:04:05.789123456z"

    def test_fromisoformat_with_fraction_and_timezone(self):
        value = DateTime.fromisoformat("2024-01-02T03:04:05.1234+00:00")
        assert value.nanosecond == 123400000
        assert value.elcl_format() == "2024-01-02 03:04:05.1234z"

    def test_fromisoformat_without_fraction(self):
        value = DateTime.fromisoformat("2024-01-02T03:04:05+02:30")
        assert value.nanosecond == 0
        assert value.tzinfo == dt.timezone(dt.timedelta(hours=2, minutes=30))
        assert value.elcl_format() == "2024-01-02 03:04:05+02:30"

    @pytest.mark.parametrize(
        ("iso", "expected"),
        [
            ("2024-01-02T03:04:05.120000+00:00", "2024-01-02t03:04:05.12z"),
            ("2024-01-02T03:04:05+02:30", "2024-01-02t03:04:05+02:30"),
        ],
    )
    def test_patch_iso_time(self, iso, expected):
        assert DateTime.patch_iso_time(iso) == expected

    def test_fromisoformat_invalid(self):
        with pytest.raises(ValueError):
            DateTime.fromisoformat("2024-13-01T03:04:05")


class TestTimeWrapper:
    @pytest.mark.parametrize(
        ("iso", "expected"),
        [
            pytest.param("03:04:05.120000+00:00", "03:04:05.12z", id="fraction_and_utc"),
            pytest.param("03:04:05.120000", "03:04:05.12", id="fraction_no_timezone"),
            pytest.param("03:04:05+00:00", "03:04:05z", id="utc_no_fraction"),
            pytest.param("03:04:05+02:30", "03:04:05+02:30", id="no_patch_needed"),
        ],
    )
    def test_patch_iso_time(self, iso, expected):
        assert Time.patch_iso_time(iso) == expected
