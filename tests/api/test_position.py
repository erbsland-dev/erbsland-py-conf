#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from erbsland.conf.location import Position


def test_default_constructor():
    pos = Position()
    assert pos.is_undefined()
    assert pos.line == -1
    assert pos.column == -1
    assert str(pos) == "undefined"


def test_parameterized_constructor():
    pos = Position(3, 7)
    assert not pos.is_undefined()
    assert pos.line == 3
    assert pos.column == 7
    assert str(pos) == "3:7"


def test_string_digit_lengths():
    pos = Position(123, 456)
    assert str(pos) == "123:456"

    pos = Position(10, 5)
    assert str(pos) == "10:5"

    pos = Position(1, 23)
    assert str(pos) == "1:23"
