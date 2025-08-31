#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from assignment_stream.as_helper import AsHelper


class TestAssignmentNumberFormats(AsHelper):

    def test_integer_formats(self):
        self.setup_from_file("integer_formats.elcl")
        self.require_section_map("decimal")
        self.require_value("decimal.value_1", 0)
        self.require_value("decimal.value_2", 1)
        self.require_value("decimal.value_3", 1)
        self.require_value("decimal.value_4", -1)
        self.require_value("decimal.value_5", 100_000)
        self.require_value("decimal.value_6", 1_000_000)
        self.require_value("decimal.value_7", -(2**63))
        self.require_value("decimal.value_8", 2**63 - 1)

        self.require_section_map("hexadecimal")
        self.require_value("hexadecimal.value_1", 0)
        self.require_value("hexadecimal.value_2", 1)
        self.require_value("hexadecimal.value_3", 1)
        self.require_value("hexadecimal.value_4", -1)
        self.require_value("hexadecimal.value_5", 0x1234ABCD)
        self.require_value("hexadecimal.value_6", -(2**63))
        self.require_value("hexadecimal.value_7", 2**63 - 1)

        self.require_section_map("binary")
        self.require_value("binary.value_1", 0)
        self.require_value("binary.value_2", 1)
        self.require_value("binary.value_3", 1)
        self.require_value("binary.value_4", -1)
        self.require_value("binary.value_5", 0b1000000111111010)
        self.require_value("binary.value_6", -(2**63))
        self.require_value("binary.value_7", 2**63 - 1)

        self.require_section_map("byte_counts")
        self.require_value("byte_counts.value_1", 5_000)
        self.require_value("byte_counts.value_2", 5_120)
        self.require_value("byte_counts.value_3", 10_000_000)
        self.require_value("byte_counts.value_4", 1_000_000_000)
        self.require_value("byte_counts.value_5", 1_000_000_000_000)
        self.require_value("byte_counts.value_6", 1_000_000_000_000_000)

    def test_float_formats(self):
        self.setup_from_file("float_formats.elcl")
        self.require_section_map("float")
        self.require_float("float.value_1", 0.0)
        self.require_float("float.value_2", 0.0)
        self.require_float("float.value_3", 1.0)
        self.require_float("float.value_4", -1.0)
        self.require_float("float.value_5", float("nan"))
        self.require_float("float.value_6", float("inf"))
        self.require_float("float.value_7", float("-inf"))
        self.require_float("float.value_8", float("inf"))
        self.require_float("float.value_9", 2937.28301)
        self.require_float("float.value_10", 5e-12)
        self.require_float("float.value_11", 0.02e8)
        self.require_float("float.value_12", 12e10)
        self.require_float("float.value_13", -12.9)
        self.require_float("float.value_14", -8_283.9e-5)
        self.require_float("float.value_15", 1_000_000.000_001)
