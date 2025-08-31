#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime as dt
import re

import pytest

from erbsland.conf.document import DocumentBuilder
from erbsland.conf.error import ConfNameConflict
from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.time_delta import TimeDelta, TimeUnit
from erbsland.conf.value_type import ValueType


class TestDocumentBuilder:
    def test_add_section_map_creates_sections(self):
        builder = DocumentBuilder()
        builder.add_section_map("main.server.filter")
        builder.add_section_map('web."settings"')
        doc = builder.get_document_and_reset()
        assert doc["main"].type == ValueType.INTERMEDIATE_SECTION
        assert doc["main.server"].type == ValueType.INTERMEDIATE_SECTION
        assert doc["main.server.filter"].type == ValueType.SECTION_WITH_NAMES
        assert doc['web."settings"'].type == ValueType.SECTION_WITH_NAMES

    @pytest.mark.parametrize(
        "native_value, expected_type",
        [
            (1, ValueType.INTEGER),
            (True, ValueType.BOOLEAN),
            (3.14, ValueType.FLOAT),
            ("text", ValueType.TEXT),
            (dt.date(2025, 12, 26), ValueType.DATE),
            (Time(22, 11, second=33), ValueType.TIME),
            (DateTime(2025, 12, 26, hour=22, minute=11, second=33), ValueType.DATE_TIME),
            (TimeDelta(5, TimeUnit.HOUR), ValueType.TIME_DELTA),
            (re.compile("abc"), ValueType.REGEX),
            (b"\x01\x02", ValueType.BYTES),
        ],
    )
    def test_add_native_value_assigns_correct_value_type(self, native_value, expected_type):
        builder = DocumentBuilder()
        builder.add_section_map("main")
        builder.add_value("main.value", native_value)
        doc = builder.get_document_and_reset()
        assert doc["main.value"].type == expected_type

    def test_reset_discards_previous_values(self):
        builder = DocumentBuilder()
        builder.add_section_map("old")
        builder.add_value("old.value", 1)
        builder.reset()
        builder.add_section_map("new")
        builder.add_value("new.value", 2)
        doc = builder.get_document_and_reset()
        flat = doc.to_flat_dict()
        assert set(str(k) for k in flat) == {"new", "new.value"}
        assert "old" not in doc

    def test_name_conflict_readding_section(self):
        builder = DocumentBuilder()
        builder.add_section_map("main.server")
        with pytest.raises(ConfNameConflict):
            builder.add_section_map("main.server")
        doc = builder.get_document_and_reset()
        flat = doc.to_flat_dict()
        assert set(str(k) for k in flat) == {"main", "main.server"}

    def test_name_conflict_readding_value(self):
        builder = DocumentBuilder()
        builder.add_section_map("main")
        builder.add_value("main.port", 8080)
        with pytest.raises(ConfNameConflict):
            builder.add_value("main.port", 9090)
        doc = builder.get_document_and_reset()
        flat = doc.to_flat_dict()
        assert doc["main.port"].as_int() == 8080
        assert set(str(k) for k in flat) == {"main", "main.port"}

    def test_name_conflict_mixing_text_and_regular_names(self):
        builder = DocumentBuilder()
        builder.add_section_map("main")
        builder.add_value('main."text"', 1)
        with pytest.raises(ConfNameConflict):
            builder.add_value("main.regular", 2)
        doc = builder.get_document_and_reset()
        assert 'main."text"' in doc
        assert "main.regular" not in doc

    def test_name_conflict_redefining_intermediate(self):
        builder = DocumentBuilder()
        builder.add_section_map("main.server.port")
        with pytest.raises(ConfNameConflict):
            builder.add_value("main.server", 1)
        with pytest.raises(ConfNameConflict):
            builder.add_section_list("main.server")
        doc = builder.get_document_and_reset()
        assert doc["main.server"].type == ValueType.INTERMEDIATE_SECTION
        assert doc["main.server.port"].type == ValueType.SECTION_WITH_NAMES

    def test_section_with_text_name_cannot_have_sub_section(self):
        builder = DocumentBuilder()
        builder.add_section_map('main."text"')
        with pytest.raises(ConfNameConflict):
            builder.add_section_map('main."text".sub')
        doc = builder.get_document_and_reset()
        assert 'main."text"' in doc
        assert 'main."text".sub' not in doc

    def test_intermediate_sections_convert(self):
        builder = DocumentBuilder()
        builder.add_section_map("one.two.three")
        builder.add_section_map("one.two")
        builder.add_section_map('alpha."beta"')
        doc = builder.get_document_and_reset()
        assert doc["one.two"].type == ValueType.SECTION_WITH_NAMES
        assert doc["one"].type == ValueType.INTERMEDIATE_SECTION
        assert doc["alpha"].type == ValueType.SECTION_WITH_TEXTS
        assert doc['alpha."beta"'].type == ValueType.SECTION_WITH_NAMES

    def test_section_list_entries_and_last_entry_handling(self):
        builder = DocumentBuilder()
        builder.add_section_map("main")
        builder.add_section_list("main.server")
        builder.add_value("name", "host1")
        builder.add_section_list("main.server")
        builder.add_value("name", "host2")
        builder.add_section_list("main.server")
        builder.add_value("name", "host3")
        builder.add_value("main.server.port", 9080)
        builder.add_section_map("main.server.details")
        builder.add_value("main.server.details.enabled", True)
        doc = builder.get_document_and_reset()
        server_list = doc["main.server"]
        assert server_list.type == ValueType.SECTION_LIST
        assert len(server_list) == 3
        assert server_list[0]["name"].as_text() == "host1"
        assert server_list[1]["name"].as_text() == "host2"
        assert server_list[2]["name"].as_text() == "host3"
        assert server_list[0].get("port") is None
        assert server_list[1].get("port") is None
        assert server_list[2]["port"].as_int() == 9080
        details = server_list[2]["details"]
        assert details.type == ValueType.SECTION_WITH_NAMES
        assert details["enabled"].as_bool() is True
