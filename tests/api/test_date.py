#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime as dt
import pytest


class TestDate:
    @pytest.mark.parametrize(
        "iso_date",
        [
            "2024-02-29",
            "1970-01-01",
        ],
    )
    def test_fromisoformat_roundtrip(self, iso_date):
        date_obj = dt.date.fromisoformat(iso_date)
        assert isinstance(date_obj, dt.date)
        assert date_obj.isoformat() == iso_date

    @pytest.mark.parametrize(
        "iso_date",
        [
            "2024-02-30",
            "2024-13-01",
        ],
    )
    def test_fromisoformat_invalid(self, iso_date):
        with pytest.raises(ValueError):
            dt.date.fromisoformat(iso_date)
