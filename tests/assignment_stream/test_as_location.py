#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from assignment_stream.as_helper import AsHelper
from erbsland.conf.location import Location, Position


class TestAssignmentStreamLocations(AsHelper):

    def require_as_and_value_location(self, assignment):
        """Make sure all required location data is set."""
        assert assignment is not None
        assert assignment.location is not None
        assert assignment.value.location is not None
        assert assignment.location.source_identifier is not None
        assert assignment.value.location.source_identifier is not None
        assert assignment.location.position is not None
        assert assignment.value.location.position is not None
        assert assignment.location.source_identifier == self.source.identifier
        assert assignment.value.location.source_identifier == self.source.identifier

    DATA_SINGLE_LINE_VALUES = [
        ("single_values.elcl", "main.value_1", "value 1:", "12345"),
        ("single_values.elcl", "main.value_2", "value 2:", "Yes"),
        ("single_values.elcl", "main.value_3", "value 3:", "12.345"),
        ("single_values.elcl", "main.value_4", "value 4:", '"This is Text"'),
        ("single_values.elcl", "main.value_5", "value 5:", "`This is Code`"),
        ("single_values.elcl", "main.value_6", "value 6:", "2026-"),
        ("single_values.elcl", "main.value_7", "value 7:", "17:54"),
        ("single_values.elcl", "main.value_8", "value 8:", "2026-"),
        ("single_values.elcl", "main.value_9", "value 9:", "<01 02"),
        ("single_values.elcl", "main.value_10", "value 10:", "10 days"),
        ("single_values.elcl", "main.value_11", "value 11:", "/regex/"),
        ("single_values.elcl", "main.value_12", "value 12:", "12345"),
        ("single_values.elcl", "main.value_13", "value 13:", '"This is Text"'),
        ("single_values.elcl", "main.value_14", "value 14:", "2026-"),
    ]

    @pytest.mark.parametrize(
        "file_name, name_path, name_marker, value_marker",
        DATA_SINGLE_LINE_VALUES,
        ids=[f"single_values_{index:03}" for index in range(len(DATA_SINGLE_LINE_VALUES))],
    )
    def test_single_line_value_locations(self, file_name, name_path, name_marker, value_marker):
        self.setup_from_file(file_name)
        expected_name_pos = self.position_at(name_marker)
        expected_value_pos = self.position_at(value_marker, name_marker)
        assignment = self.find_assignment(name_path)
        self.require_as_and_value_location(assignment)
        as_pos = assignment.location.position
        assert as_pos == expected_name_pos
        value_pos = assignment.value.location.position
        assert value_pos == expected_value_pos

    DATA_MULTI_LINE_VALUES = [
        ("multiline_values.elcl", "text.value_1", "[text]", "value 1:", '"""'),
        ("multiline_values.elcl", "text.value_2", "[text]", "value 2:", '"""'),
        ("multiline_values.elcl", "text.value_3", "[text]", "value 3:", '"""'),
        ("multiline_values.elcl", "text.value_4", "[text]", "value 4:", '"""'),
        ("multiline_values.elcl", "text.value_5", "[text]", "value 5:", '"""'),
        ("multiline_values.elcl", "code.value_1", "[code]", "value 1:", "```"),
        ("multiline_values.elcl", "code.value_2", "[code]", "value 2:", "```"),
        ("multiline_values.elcl", "code.value_3", "[code]", "value 3:", "```"),
        ("multiline_values.elcl", "code.value_4", "[code]", "value 4:", "```"),
        ("multiline_values.elcl", "code.value_5", "[code]", "value 5:", "```"),
        ("multiline_values.elcl", "regex.value_1", "[regex]", "value 1:", "///"),
        ("multiline_values.elcl", "regex.value_2", "[regex]", "value 2:", "///"),
        ("multiline_values.elcl", "regex.value_3", "[regex]", "value 3:", "///"),
        ("multiline_values.elcl", "regex.value_4", "[regex]", "value 4:", "///"),
        ("multiline_values.elcl", "regex.value_5", "[regex]", "value 5:", "///"),
        ("multiline_values.elcl", "bytes.value_1", "[bytes]", "value 1:", "<<<"),
        ("multiline_values.elcl", "bytes.value_2", "[bytes]", "value 2:", "<<<"),
        ("multiline_values.elcl", "bytes.value_3", "[bytes]", "value 3:", "<<<"),
        ("multiline_values.elcl", "bytes.value_4", "[bytes]", "value 4:", "<<<"),
    ]

    @pytest.mark.parametrize(
        "file_name, name_path, section_marker, name_marker, value_marker",
        DATA_MULTI_LINE_VALUES,
        ids=[f"multi_line_values_{index:03}" for index in range(len(DATA_MULTI_LINE_VALUES))],
    )
    def test_multi_line_value_locations(self, file_name, name_path, section_marker, name_marker, value_marker):
        self.setup_from_file(file_name)
        expected_name_pos = self.position_at(name_marker, section_marker)
        expected_value_pos = self.position_at(value_marker, [section_marker, name_marker])
        assignment = self.find_assignment(name_path)
        self.require_as_and_value_location(assignment)
        as_pos = assignment.location.position
        assert as_pos == expected_name_pos
        value_pos = assignment.value.location.position
        assert value_pos == expected_value_pos

    DATA_META_VALUES = [
        ("@signature", "@signature"),
        ("@version", "@version"),
        ("@features", "@features"),
        ("@include", "@include"),
    ]

    @pytest.mark.parametrize(
        "name_path, marker",
        DATA_META_VALUES,
        ids=[f"meta_values_{index:03}" for index in range(len(DATA_META_VALUES))],
    )
    def test_meta_value_locations(self, name_path, marker):
        self.setup_from_file("meta.elcl")
        expected_name_pos = self.position_at(marker)
        expected_value_pos = self.position_at('"', marker)
        assignment = self.find_assignment(name_path)
        self.require_as_and_value_location(assignment)
        as_pos = assignment.location.position
        assert as_pos == expected_name_pos
        value_pos = assignment.value.location.position
        assert value_pos == expected_value_pos

    DATA_SINGLE_LINE_LISTS = [
        ("main.value_1", "value 1:", "1", "1", 0),
        ("main.value_1", "value 1:", "1", "2", 1),
        ("main.value_1", "value 1:", "1", "3", 2),
        ("main.value_2", "value 2:", '"one"', '"one"', 0),
        ("main.value_2", "value 2:", '"one"', '"two"', 1),
        ("main.value_2", "value 2:", '"one"', '"three"', 2),
        ("main.value_2", "value 2:", '"one"', '"four"', 3),
        ("main.value_2", "value 2:", '"one"', '"five"', 4),
        ("main.value_3", "value 3:", "98765", "98765", 0),
        ("main.value_3", "value 3:", "98765", "disabled", 1),
        ("main.value_3", "value 3:", "98765", "98.76", 2),
        ("main.value_3", "value 3:", "98765", '"-text-"', 3),
        ("main.value_3", "value 3:", "98765", "`{code}`", 4),
        ("main.value_3", "value 3:", "98765", "2028-01-30", 5),
        ("main.value_3", "value 3:", "98765", "<a1 b2 c3>", 6),
        ("main.value_4", "value 4:", '"-text-"', '"-text-"', 0),
        ("main.value_4", "value 4:", '"-text-"', "4567", 1),
    ]

    @pytest.mark.parametrize(
        "name_path, name_marker, list_marker, value_marker, value_index",
        DATA_SINGLE_LINE_LISTS,
        ids=[f"single_line_lists_{index:03}" for index in range(len(DATA_SINGLE_LINE_LISTS))],
    )
    def test_single_line_value_list_locations(self, name_path, name_marker, list_marker, value_marker, value_index):
        self.setup_from_file("value_lists.elcl")
        expected_name_pos = self.position_at(name_marker)
        expected_list_pos = self.position_at(list_marker, name_marker)
        expected_value_pos = self.position_at(value_marker, name_marker)
        assignment = self.find_assignment(name_path)
        self.require_as_and_value_location(assignment)
        as_pos = assignment.location.position
        assert as_pos == expected_name_pos
        list_pos = assignment.value.location.position
        assert list_pos == expected_list_pos
        value = assignment.value[value_index]
        assert value.location is not None
        value_pos = value.location.position
        assert value_pos == expected_value_pos

    DATA_MULTI_LINE_LISTS = [
        ("main.value_5", "value 5:", "*", "111", 0),
        ("main.value_5", "value 5:", "*", "222", 1),
        ("main.value_5", "value 5:", "*", "333", 2),
        ("main.value_5", "value 5:", "*", "444", 3),
        ("main.value_5", "value 5:", "*", "555", 4),
        ("main.value_6", "value 6:", "*", '"😀"', 0),
        ("main.value_6", "value 6:", "*", "34566", 1),
        ("main.value_6", "value 6:", "*", "77.77", 2),
        ("main.value_6", "value 6:", "*", '`a = "😆"`', 3),
        ("main.value_6", "value 6:", "*", "off", 4),
    ]

    @pytest.mark.parametrize(
        "name_path, name_marker, list_marker, value_marker, value_index",
        DATA_MULTI_LINE_LISTS,
        ids=[f"multi_line_lists_{index:03}" for index in range(len(DATA_MULTI_LINE_LISTS))],
    )
    def test_multi_line_value_list_locations(self, name_path, name_marker, list_marker, value_marker, value_index):
        self.setup_from_file("value_lists.elcl")
        expected_name_pos = self.position_at(name_marker)
        expected_list_pos = self.position_at(list_marker, name_marker)
        expected_value_pos = self.position_at(value_marker, name_marker)
        assignment = self.find_assignment(name_path)
        self.require_as_and_value_location(assignment)
        as_pos = assignment.location.position
        assert as_pos == expected_name_pos
        list_pos = assignment.value.location.position
        assert list_pos == expected_list_pos
        value = assignment.value[value_index]
        assert value.location is not None
        value_pos = value.location.position
        assert value_pos == expected_value_pos

    def _partial_equal(self, p1: Position, p2: Position) -> bool:
        return p1.line == p2.line and p1.column == p2.column

    def test_list_matrix(self):
        self.setup_from_file("value_lists.elcl")
        assignment = self.find_assignment("main.value_7")
        self.require_as_and_value_location(assignment)
        value = assignment.value
        assert self._partial_equal(value.location.position, Position(25, 5))
        assert self._partial_equal(value[0].location.position, Position(25, 5))
        assert self._partial_equal(value[1].location.position, Position(26, 5))
        assert self._partial_equal(value[7].location.position, Position(32, 5))
        assert self._partial_equal(value[0][0].location.position, Position(25, 10))
        assert self._partial_equal(value[0][1].location.position, Position(25, 15))
        assert self._partial_equal(value[0][7].location.position, Position(25, 44))
        assert self._partial_equal(value[1][0].location.position, Position(26, 10))
        assert self._partial_equal(value[7][7].location.position, Position(32, 44))

    DATA_SECTION_MAPS = [
        ("main", "[main]"),
        ("main.server.filter", "[.server.filter]"),
        ("main.client.filter", "-----[   .client.Filter   ]-----"),
        ('text."First Text"', '[Text."First Text"]'),
        ('text."Second Text"', '-----[   text . "Second Text"   ]-----'),
    ]

    @pytest.mark.parametrize(
        "name_path, marker",
        DATA_SECTION_MAPS,
        ids=[f"section_maps_{index:03}" for index in range(len(DATA_SECTION_MAPS))],
    )
    def test_section_map_locations(self, name_path, marker):
        self.setup_from_file("sections.elcl")
        expected_pos = self.position_at(marker)
        assignment = self.find_assignment(name_path)
        assert assignment.location is not None
        as_pos = assignment.location.position
        assert as_pos == expected_pos

    DATA_SECTION_LISTS = [
        ("server", "*[server]", 0),
        ("server", "*[server]  # Another entry.", 1),
        ("server", "----*[ server ]*-----", 2),
        ("client.config", "*[client.config]", 0),
        ("client.config", "*[client.config]*", 1),
        ("client.config", "-------*[ client . config ]*", 2),
    ]

    @pytest.mark.parametrize(
        "name_path, section_marker, section_index",
        DATA_SECTION_LISTS,
        ids=[f"section_lists_{index:03}" for index in range(len(DATA_SECTION_LISTS))],
    )
    def test_section_list_locations(self, name_path, section_marker, section_index):
        self.setup_from_file("section_lists.elcl")
        expected_pos = self.position_at(section_marker)
        assignment = self.find_assignment(name_path, section_index)
        assert assignment.location is not None
        as_pos = assignment.location.position
        assert as_pos == expected_pos
