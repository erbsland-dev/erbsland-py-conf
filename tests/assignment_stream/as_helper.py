#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from pathlib import Path
import math

import pytest

from erbsland.conf.impl.assignment import AssignmentStream, Assignment, AssignmentType
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.value_storage_type import (
    ValueStorageType,
    is_valid_storage_value,
    value_type_from_storage_type,
)
from erbsland.conf.location import Position
from erbsland.conf.name_path import NamePath
from erbsland.conf.value_type import ValueType


StartAfterParam = str | list[str] | None


class AsHelper:

    def setup_from_file(self, file_name: str):
        path = Path(__file__).parent / "data" / file_name
        self.content = path.read_text()
        self.source = FileSource(path)
        self.source.open()
        self.lexer = Lexer(self.source, digest_enabled=True)
        self.assignment_stream = AssignmentStream(self.lexer, self.source.identifier)
        self.generator = self.assignment_stream.assignments()

    def next_assignment(self) -> Assignment:
        assignment = next(self.generator)
        assert assignment is not None
        return assignment

    def require_end(self):
        assignment = self.next_assignment()
        assert assignment.is_end_of_document()

    def require_section_map(self, name_path: str | NamePath):
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.SECTION_MAP
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        assert assignment.name_path == name_path

    def require_section_list(self, name_path: str | NamePath):
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.SECTION_LIST
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        assert assignment.name_path == name_path

    def require_value(self, name_path: str | NamePath, value: ValueStorageType | list[ValueStorageType]):
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.VALUE
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        assert assignment.name_path == name_path
        if isinstance(value, list):
            assert assignment.value.type == ValueType.VALUE_LIST
            for index, expected_value in enumerate(value):
                assert is_valid_storage_value(expected_value)
                value_type = value_type_from_storage_type(type(expected_value))
                as_value = assignment.value[index]
                assert as_value.type == value_type
                assert as_value.native == expected_value
        else:
            assert is_valid_storage_value(value)
            value_type = value_type_from_storage_type(type(value))
            assert assignment.value.type == value_type
            assert (
                assignment.value.native == value
            ), f"Values aren't equal (actual == expected): {assignment.value.native} == {value}"

    def require_meta_value(self, name_path: str | NamePath, text: str):
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.META_VALUE
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        assert assignment.name_path == name_path
        assert assignment.value.type == ValueType.TEXT
        assert assignment.value.native == text

    def require_float(self, name_path: str | NamePath, value: float):
        assignment = self.next_assignment()
        assert assignment.type == AssignmentType.VALUE
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        assert assignment.name_path == name_path
        assert assignment.value.type == ValueType.FLOAT
        actual = assignment.value.native
        if math.isnan(value):
            assert math.isnan(actual)
        elif math.isinf(value):
            assert math.isinf(actual) and (actual > 0) == (value > 0)
        else:
            assert actual == pytest.approx(value)

    def position_from_index(self, index: int) -> Position:
        """Get the position of a character based on its index."""
        line = self.content.count("\n", 0, index) + 1
        last_nl = self.content.rfind("\n", 0, index)
        column = index - last_nl if last_nl != -1 else index + 1
        return Position(line, column, index)

    def index_after(self, start_after: StartAfterParam) -> int:
        if start_after is None:
            return 0
        if isinstance(start_after, str):
            start_after = [start_after]
        index = 0
        for marker in start_after:
            index = self.content.index(marker, index)
            index += len(marker)
        return index

    def position_at(self, marker: str, start_after: StartAfterParam = None) -> Position:
        start = self.index_after(start_after)
        idx = self.content.index(marker, start)
        return self.position_from_index(idx)

    def position_after(self, marker: str, start_after: StartAfterParam = None) -> Position:
        start = self.index_after(start_after)
        idx = self.content.index(marker, start) + len(marker)
        return self.position_from_index(idx)

    def find_assignment(self, name_path: str | NamePath, skip_count: int = 0) -> Assignment:
        if isinstance(name_path, str):
            name_path = NamePath.from_text(name_path)
        while True:
            assignment = self.next_assignment()
            if assignment.is_end_of_document():
                raise AssertionError(f"{name_path} not found")
            if assignment.name_path == name_path:
                if skip_count > 0:
                    skip_count -= 1
                    continue
                return assignment
        raise AssertionError(f"{name_path} not found")
