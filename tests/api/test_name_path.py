#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfSyntaxError, ConfCharacterError, ConfLimitExceeded, Error
from erbsland.conf.name_path import NamePath
from erbsland.conf.name import Name


def names_from_path(path):
    return list(path)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", NamePath()),
        (
            "one.two.three",
            NamePath(
                [
                    Name.create_regular("one"),
                    Name.create_regular("two"),
                    Name.create_regular("three"),
                ]
            ),
        ),
        (
            "   Name1 . Name2 . Name 3  ",
            NamePath(
                [
                    Name.create_regular("name1"),
                    Name.create_regular("name2"),
                    Name.create_regular("name_3"),
                ]
            ),
        ),
        (
            'server[12].info." This is a text"',
            NamePath(
                [
                    Name.create_regular("server"),
                    Name.create_index(12),
                    Name.create_regular("info"),
                    Name.create_text(" This is a text"),
                ]
            ),
        ),
        (
            "[12][34]",
            NamePath([Name.create_index(12), Name.create_index(34)]),
        ),
        (
            "server.value[12][34]",
            NamePath(
                [
                    Name.create_regular("server"),
                    Name.create_regular("value"),
                    Name.create_index(12),
                    Name.create_index(34),
                ]
            ),
        ),
        (
            'server.text.""[1234].filter',
            NamePath(
                [
                    Name.create_regular("server"),
                    Name.create_regular("text"),
                    Name.create_text_index(1234),
                    Name.create_regular("filter"),
                ]
            ),
        ),
        (
            '"a text".value',
            NamePath(
                [
                    Name.create_text("a text"),
                    Name.create_regular("value"),
                ]
            ),
        ),
        (
            "@version",
            NamePath([Name.create_regular("@version")]),
        ),
    ],
)
def test_from_text_valid(text, expected):
    np = NamePath.from_text(text)
    assert np == expected


@pytest.mark.parametrize(
    "invalid_text,expected_error",
    [
        (".", ConfSyntaxError),
        ("name\n.name", ConfSyntaxError),
        ("name\r.name", ConfSyntaxError),
        ("name..name", ConfSyntaxError),
        ("name.", ConfSyntaxError),
        ("name.value.", ConfSyntaxError),
        (" name   .. name", ConfSyntaxError),
        (" name  .  ", ConfSyntaxError),
        ("  name  .   value   .  ", ConfSyntaxError),
        ("9name.value", ConfSyntaxError),
        ("name.9value", ConfSyntaxError),
        ("name[x]", ConfSyntaxError),
        ("name.[10]", ConfSyntaxError),
        ("name.value[x]", ConfSyntaxError),
        ("name[0]name", ConfSyntaxError),
        ("main.Name  Name", ConfSyntaxError),
        ('main." text "name', ConfSyntaxError),
        ("main._value", ConfSyntaxError),
        ("main.value_", ConfSyntaxError),
        ("main.value__value", ConfSyntaxError),
        ("main.value _value", ConfSyntaxError),
        ("main.value_ value", ConfSyntaxError),
        pytest.param("a" * 5000, ConfLimitExceeded, id="name_too_long#1"),
        pytest.param("main.name" + "a" * 100 + ".value", ConfLimitExceeded, id="name_too_long#2"),
        ('main.""', ConfSyntaxError),
        ('main."".value', ConfSyntaxError),
        ('main."""\n', ConfSyntaxError),
        ('main."\n".value', ConfSyntaxError),
        ('main."\\x".value', ConfSyntaxError),
        ('main.\\"text".value', ConfSyntaxError),
        ('main."text\\".value', ConfSyntaxError),
    ],
)
def test_from_text_invalid(invalid_text, expected_error):
    with pytest.raises(expected_error):
        NamePath.from_text(invalid_text)


@pytest.mark.parametrize(
    "path, expected",
    [
        (NamePath(), ""),
        (
            NamePath(
                [
                    Name.create_regular("one"),
                    Name.create_regular("two"),
                    Name.create_regular("three"),
                ]
            ),
            "one.two.three",
        ),
        (
            NamePath([Name.create_text_index(1234), Name.create_regular("value")]),
            '""[1234].value',
        ),
        (
            NamePath(
                [
                    Name.create_regular("value"),
                    Name.create_text_index(1234),
                    Name.create_text_index(0),
                ]
            ),
            'value.""[1234].""[0]',
        ),
    ],
)
def test_to_text(path, expected):
    assert path.to_text() == expected
    assert NamePath.from_text(path.to_text()) == path


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", ""),
        ("one.two.three", "one.two.three"),
        ("   Name1 . Name2 . Name 3  ", "name1.name2.name_3"),
        ('server[12].info." This is a text"', 'server[12].info." This is a text"'),
        ("[12][34]", "[12][34]"),
        ("server.value[12][34]", "server.value[12][34]"),
        ('server.text.""[1234].filter', 'server.text.""[1234].filter'),
        ('"a text".value', '"a text".value'),
        ("@version", "@version"),
    ],
)
def test_to_text_from_text_round_trip(text, expected):
    path = NamePath.from_text(text)
    assert path.to_text() == expected
    assert NamePath.from_text(path.to_text()) == path


def test_text_name_escape_round_trip():
    text = 'Line\nBreak\rCarriage\tTab$Dollar"Quote\\Backslash.:=' + chr(1) + "ä"
    name = Name.create_text(text)
    path = NamePath([name])
    expected = (
        '"Line\\u{a}Break\\u{d}Carriage\\u{9}Tab$Dollar\\u{22}Quote\\u{5c}Backslash\\u{2e}\\u{3a}\\u{3d}\\u{1}\\u{e4}"'
    )
    assert path.to_text() == expected
    name_path = NamePath.from_text(expected)
    assert len(name_path) == 1
    text_element = name_path[0]
    assert text_element.is_text()
    assert text_element.as_text() == text


@pytest.mark.parametrize(
    "text, escaped",
    [
        (".", "\\u{2e}"),
        (":", "\\u{3a}"),
        ("=", "\\u{3d}"),
        ("\\", "\\u{5c}"),
        ('"', "\\u{22}"),
        ("ä", "\\u{e4}"),
        ("$", "$"),
    ],
)
def test_text_name_to_text_escape(text, escaped):
    path = NamePath([Name.create_text(text)])
    expected = f'"{escaped}"'
    assert path.to_text() == expected
    assert NamePath.from_text(expected) == path


@pytest.mark.parametrize(
    "escaped, char",
    [
        ("\\n", "\n"),
        ("\\r", "\r"),
        ("\\t", "\t"),
        ("\\$", "$"),
        ('\\"', '"'),
        ("\\\\", "\\"),
        ("\\u0041", "A"),
        ("\\u{41}", "A"),
        ("\\u{2e}", "."),
        ("\\u{3a}", ":"),
        ("\\u{3d}", "="),
        ("\\u{e4}", "ä"),
    ],
)
def test_text_name_from_text_unescape(escaped, char):
    path = NamePath.from_text(f'"start{escaped}end"')
    assert list(path) == [Name.create_text(f"start{char}end")]


@pytest.mark.parametrize(
    "invalid",
    [
        "\\x",
        "\\u",
        "\\u0",
        "\\u000",
        "\\u{",
        "\\u{}",
        "\\u{110000}",
        "\\u{d800}",
        "\\u0000",
    ],
)
def test_text_name_from_text_invalid(invalid):
    with pytest.raises(ConfSyntaxError):
        NamePath.from_text(f'"test{invalid}"')


def test_get_item_slice_and_errors():
    path = NamePath.from_text("a.b.c")
    assert path[1] == Name.create_regular("b")
    assert path[1:].to_text() == "b.c"
    with pytest.raises(TypeError):
        _ = path[1.5]
    with pytest.raises(IndexError):
        _ = path[3]


def test_eq_lt_and_notimplemented():
    path_a = NamePath.from_text("a")
    path_b = NamePath.from_text("b")
    assert path_a == NamePath.from_text("a")
    assert path_a != path_b
    assert path_a < path_b
    assert NamePath.__eq__(path_a, object()) is NotImplemented
    assert NamePath.__lt__(path_a, object()) is NotImplemented
    assert isinstance(hash(path_a), int)


def test_truediv_cases_and_errors():
    path = NamePath.from_text("a")
    assert (path / Name.create_regular("b")).to_text() == "a.b"
    assert (path / NamePath.from_text("c.d")).to_text() == "a.c.d"
    with pytest.raises(ValueError):
        _ = path / "e.f"
    with pytest.raises(TypeError):
        _ = path / 1


def test_copy_and_copy_module():
    import copy as pycopy

    original = NamePath.from_text("a.b")
    clone = original.copy()
    assert clone == original and clone is not original
    clone.append("c")
    assert clone.to_text() == "a.b.c"
    assert original.to_text() == "a.b"
    clone2 = pycopy.copy(original)
    assert clone2 == original and clone2 is not original


def test_append_types_and_error():
    path = NamePath.from_text("a")
    path.append(Name.create_regular("b"))
    path.append(NamePath.from_text("c.d"))
    path.append("e.f")
    assert path.to_text() == "a.b.c.d.e.f"
    with pytest.raises(TypeError):
        path.append(1)


def test_repr_and_str():
    assert repr(NamePath()) == "NamePath()"
    path = NamePath.from_text("a.b")
    assert repr(path) == "NamePath(a.b)"
    assert str(path) == "a.b"
