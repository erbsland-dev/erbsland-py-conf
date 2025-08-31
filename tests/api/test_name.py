#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfCharacterError, ConfLimitExceeded, ConfSyntaxError
from erbsland.conf.name import Name, NameType, RegularName, TextName
from erbsland.conf.impl.limits import MAX_LINE_LENGTH, MAX_NAME_LENGTH


class TestName:
    def test_regular_name_creation_and_properties(self):
        name = Name.create_regular("Name Value")
        assert name.type is NameType.REGULAR
        assert name.is_regular()
        assert not name.is_text()
        assert not name.is_index()
        assert not name.is_text_index()
        assert not name.is_meta()
        assert name.as_text() == "name_value"
        assert name.to_path_text() == "name_value"
        assert str(name) == "name_value"
        with pytest.raises(TypeError):
            name.as_index()

    def test_is_meta(self):
        meta = Name.create_regular("@Meta")
        assert meta.is_meta()
        non_meta = Name.create_regular("name")
        assert not non_meta.is_meta()
        assert not Name.create_text("@meta").is_meta()

    def test_text_name_creation_and_properties(self):
        name = Name.create_text("some text")
        assert name.type is NameType.TEXT
        assert not name.is_regular()
        assert name.is_text()
        assert not name.is_index()
        assert not name.is_text_index()
        assert name.as_text() == "some text"
        assert name.to_path_text() == '"some text"'
        with pytest.raises(TypeError):
            name.as_index()

    def test_index_name_creation_and_properties(self):
        name = Name.create_index(3)
        assert name.type is NameType.INDEX
        assert not name.is_regular()
        assert not name.is_text()
        assert name.is_index()
        assert not name.is_text_index()
        assert name.as_index() == 3
        assert name.to_path_text() == "[3]"
        assert str(name) == "[3]"
        with pytest.raises(TypeError):
            name.as_text()

    def test_text_index_name_creation_and_properties(self):
        name = Name.create_text_index(4)
        assert name.type is NameType.TEXT_INDEX
        assert not name.is_regular()
        assert not name.is_text()
        assert not name.is_index()
        assert name.is_text_index()
        assert name.as_index() == 4
        assert name.to_path_text() == '""[4]'
        with pytest.raises(TypeError):
            name.as_text()

    def test_to_path_text_unknown_type(self):
        name = Name.create_regular("a")
        object.__setattr__(name, "_type", None)
        assert name.to_path_text() == ""

    def test_normalize(self):
        assert Name.normalize("Name Value") == "name_value"

    def test_normalize_invalid(self):
        with pytest.raises(ValueError):
            Name.normalize("invalid$Name")

    @pytest.mark.parametrize(
        "text, error",
        [
            pytest.param("", ValueError, id="empty"),
            pytest.param(123, ValueError, id="not_string"),
            pytest.param("a" * (MAX_LINE_LENGTH + 1), ConfLimitExceeded, id="too_long"),
            pytest.param("bad\x00char", ConfCharacterError, id="null_char"),
        ],
    )
    def test_validate_text_invalid(self, text, error):
        with pytest.raises(error):
            Name.validate_text(text)  # type: ignore[arg-type]

    def test_validate_text_valid(self):
        Name.validate_text("ok")

    @pytest.mark.parametrize(
        "name_value, error",
        [
            pytest.param("", ValueError, id="empty"),
            pytest.param(123, ValueError, id="not_string"),
            pytest.param("a" * (MAX_NAME_LENGTH + 1), ConfLimitExceeded, id="too_long"),
            pytest.param(" name", ConfSyntaxError, id="starts_space"),
            pytest.param("name ", ConfSyntaxError, id="ends_space"),
            pytest.param("name_", ConfSyntaxError, id="ends_underscore"),
            pytest.param("na$me", ConfSyntaxError, id="invalid_char"),
            pytest.param("@", ConfSyntaxError, id="empty_meta"),
            pytest.param("9name", ConfSyntaxError, id="starts_digit"),
            pytest.param("@9name", ConfSyntaxError, id="meta_starts_digit"),
            pytest.param("name__value", ConfSyntaxError, id="double_sep"),
            pytest.param("name  value", ConfSyntaxError, id="double_space"),
        ],
    )
    def test_validate_regular_name_invalid(self, name_value, error):
        with pytest.raises(error):
            Name.validate_regular_name(name_value)  # type: ignore[arg-type]

    def test_validate_regular_name_valid(self):
        Name.validate_regular_name("valid_name")

    @pytest.mark.parametrize(
        "raw, expected",
        [
            pytest.param("Name", Name.create_regular("Name"), id="regular"),
            pytest.param('"Text"', Name.create_text("Text"), id="text"),
        ],
    )
    def test_from_document_valid(self, raw, expected):
        assert Name.from_document(raw) == expected

    @pytest.mark.parametrize(
        "raw, error",
        [
            pytest.param("", ValueError, id="empty"),
            pytest.param(123, ValueError, id="not_string"),
            pytest.param('"no_end', ValueError, id="no_end_quote"),
            pytest.param('""', ConfSyntaxError, id="empty_text"),
            pytest.param('"\\x"', ConfSyntaxError, id="invalid_escape"),
            pytest.param("9name", ConfSyntaxError, id="invalid_regular"),
        ],
    )
    def test_from_document_invalid(self, raw, error):
        with pytest.raises(error):
            Name.from_document(raw)  # type: ignore[arg-type]

    def test_post_init_invalid(self):
        with pytest.raises(ValueError):
            Name(NameType.REGULAR, 1)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Name(NameType.TEXT, 1)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Name(NameType.TEXT, "")
        with pytest.raises(ValueError):
            Name(NameType.INDEX, "1")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Name(NameType.INDEX, -1)
        with pytest.raises(ValueError):
            Name(NameType.TEXT_INDEX, "1")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Name(NameType.TEXT_INDEX, -1)
        with pytest.raises(ValueError):
            Name(NameType.REGULAR, "bad$")

    def test_as_text_index_errors(self):
        with pytest.raises(TypeError):
            Name.create_index(0).as_text()
        with pytest.raises(TypeError):
            Name.create_regular("a").as_index()

    def test_comparison(self):
        a = Name.create_regular("a")
        b = Name.create_regular("b")
        i = Name.create_index(0)
        assert a < b
        assert (i < a) is False  # comparison across types is stable
        assert a.__lt__(5) is NotImplemented

    def test_helper_constructors(self):
        assert RegularName("Name") == Name.create_regular("Name")
        assert TextName("text") == Name.create_text("text")
