#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import pytest
import datetime as dt

from erbsland.conf.datetime import Time


class TestDateTime:

    @pytest.mark.parametrize(
        "iso_time",
        [
            "01:02:03",
            "01:02:03.1",
            "01:02:03.12",
            "01:02:03.123",
            "01:02:03.1234",
            "01:02:03.12345",
            "01:02:03.123456",
            "01:02:03.1234567",
            "01:02:03.12345678",
            "01:02:03.123456789",
            "01:02:03.001",
            "01:02:03.00001",
            "01:02:03.0000001",
            "01:02:03.000000001",
        ],
    )
    def test_datetime_parse(self, iso_time):
        time = Time.fromisoformat(iso_time)
        assert time is not None
        assert isinstance(time, Time)
        assert isinstance(time, dt.time)
        time_str = time.elcl_format()
        assert time_str == iso_time
