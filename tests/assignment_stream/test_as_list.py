#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime

from assignment_stream.as_helper import AsHelper
from erbsland.conf.impl.assignment import AssignmentType
from erbsland.conf.name_path import NamePath
from erbsland.conf.value_type import ValueType


class TestAssignmentStreamList(AsHelper):

    def test_value_lists(self):
        self.setup_from_file("value_lists.elcl")
        self.require_section_map("main")
        self.require_value("main.value_1", [1, 2, 3, 4, 5])
        self.require_value("main.value_2", ["one", "two", "three", "four", "five"])
        self.require_value(
            "main.value_3",
            [
                98765,
                False,
                98.76,
                "-text-",
                "{code}",
                datetime.date(2028, 1, 30),
                bytes.fromhex("a1 b2 c3"),
            ],
        )
        self.require_value("main.value_4", ["-text-", 4567])
        self.require_value("main.value_5", [111, 222, 333, 444, 555])
        self.require_value(
            "main.value_6",
            ["😀", 34566, 77.77, 'a = "😆"', False],
        )
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.VALUE
        assert assignment.name_path == NamePath.from_text("main.value_7")
        assert assignment.value.type == ValueType.VALUE_LIST
        expected = [
            [1, 3, 6, 10, 15, 21, 28, 36],
            [2, 5, 9, 14, 20, 27, 35, 44],
            [3, 7, 12, 18, 25, 33, 42, 52],
            [4, 9, 15, 22, 30, 39, 49, 60],
            [5, 11, 18, 26, 35, 45, 56, 68],
            [6, 13, 21, 30, 40, 51, 63, 76],
            [7, 15, 24, 34, 45, 57, 70, 84],
            [8, 17, 27, 38, 50, 63, 77, 92],
        ]
        for i, row_expected in enumerate(expected):
            row_value = assignment.value[i]
            assert row_value.type == ValueType.VALUE_LIST
            for j, col_expected in enumerate(row_expected):
                value = row_value[j]
                assert value.type == ValueType.INTEGER
                assert value.native == col_expected
        self.require_end()
