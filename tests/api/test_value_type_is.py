#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.value_type import ValueType


class TestValueTypeIsMethods:
    @pytest.mark.parametrize(
        ("method_name", "expected"),
        [
            (
                "is_single_value",
                {
                    ValueType.INTEGER,
                    ValueType.BOOLEAN,
                    ValueType.FLOAT,
                    ValueType.TEXT,
                    ValueType.DATE,
                    ValueType.TIME,
                    ValueType.DATE_TIME,
                    ValueType.BYTES,
                    ValueType.TIME_DELTA,
                    ValueType.REGEX,
                },
            ),
            ("is_list", {ValueType.VALUE_LIST, ValueType.SECTION_LIST}),
            (
                "is_map",
                {
                    ValueType.INTERMEDIATE_SECTION,
                    ValueType.SECTION_WITH_NAMES,
                    ValueType.SECTION_WITH_TEXTS,
                    ValueType.DOCUMENT,
                },
            ),
            (
                "is_container",
                {
                    ValueType.VALUE_LIST,
                    ValueType.SECTION_LIST,
                    ValueType.INTERMEDIATE_SECTION,
                    ValueType.SECTION_WITH_NAMES,
                    ValueType.SECTION_WITH_TEXTS,
                    ValueType.DOCUMENT,
                },
            ),
            (
                "is_section",
                {
                    ValueType.INTERMEDIATE_SECTION,
                    ValueType.SECTION_WITH_NAMES,
                    ValueType.SECTION_WITH_TEXTS,
                    ValueType.DOCUMENT,
                    ValueType.SECTION_LIST,
                },
            ),
        ],
    )
    def test_is_methods(self, method_name, expected):
        actual = {value_type for value_type in ValueType if getattr(value_type, method_name)()}
        assert actual == expected
