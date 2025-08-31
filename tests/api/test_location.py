#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest
from erbsland.conf.location import Location, Position
from erbsland.conf.source import SourceIdentifier


def test_location_with_position():
    src_id = SourceIdentifier(SourceIdentifier.FILE, "file.elcl")
    pos = Position(42, 10)
    loc = Location(src_id, pos)

    assert loc.source_identifier is src_id
    assert loc.position is pos
    assert loc.position.line == 42
    assert loc.position.column == 10


def test_location_default_position():
    src_id = SourceIdentifier(SourceIdentifier.TEXT, "")
    loc = Location(src_id)

    assert loc.source_identifier is src_id
    assert loc.position.is_undefined()


@pytest.mark.parametrize(
    "position, expected",
    [
        pytest.param(Position(3, 5), "file:/tmp/example.elcl:[3:5]", id="defined"),
        pytest.param(Position(), "file:/tmp/example.elcl:[undefined]", id="undefined"),
    ],
)
def test_location_str(position, expected):
    src_id = SourceIdentifier(SourceIdentifier.FILE, "/tmp/example.elcl")
    loc = Location(src_id, position)
    assert str(loc) == expected
    assert str(loc) == loc.to_text()


@pytest.mark.parametrize(
    "compact, expected",
    [
        pytest.param(False, "file:/path/to/config.elcl:[1:2]", id="full"),
        pytest.param(True, "file:config.elcl:[1:2]", id="compact"),
    ],
)
def test_location_to_text(compact, expected):
    src_id = SourceIdentifier(SourceIdentifier.FILE, "/path/to/config.elcl")
    loc = Location(src_id, Position(1, 2))
    assert loc.to_text(compact=compact) == expected
