#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import datetime
import re

from assignment_stream.as_helper import AsHelper
from erbsland.conf.time_delta import TimeDelta, TimeUnit


class TestAssignmentStreamBasic(AsHelper):

    def test_basic_functionality(self):
        self.setup_from_file("basic.elcl")
        self.require_section_map("main")
        self.require_value("main.server", "host01.example.com")
        self.require_value("main.port", 123456)
        self.require_end()

    def test_single_values(self):
        self.setup_from_file("single_values.elcl")
        self.require_section_map("main")
        self.require_value("main.value_1", 12345)
        self.require_value("main.value_2", True)
        self.require_value("main.value_3", 12.345)
        self.require_value("main.value_4", "This is Text")
        self.require_value("main.value_5", "This is Code")
        self.require_value("main.value_6", datetime.date(2026, 8, 10))
        self.require_value("main.value_7", datetime.time(17, 54, 12, 0, tzinfo=datetime.UTC))
        self.require_value("main.value_8", datetime.datetime(2026, 8, 10, 17, 54, 12, 0, tzinfo=datetime.UTC))
        self.require_value("main.value_9", b"\x01\x02\x03\xfd\xfe\xff")
        self.require_value("main.value_10", TimeDelta(10, TimeUnit.DAY))
        self.require_value("main.value_11", re.compile(r"regex"))
        self.require_value("main.value_12", 12345)
        self.require_value("main.value_13", "This is Text")
        self.require_value("main.value_14", datetime.date(2026, 8, 10))

    def test_multi_line_values(self):
        self.setup_from_file("multiline_values.elcl")
        self.require_section_map("text")
        self.require_value("text.value_1", "Hello World!")
        self.require_value("text.value_2", "\nHello World!\n")
        self.require_value("text.value_3", "Hello World!")
        self.require_value("text.value_4", "    Hello World!")
        self.require_value("text.value_5", "The first line.\nA second line.\nThird line of text.")
        self.require_section_map("code")
        self.require_value("code.value_1", "Code\\n")
        self.require_value("code.value_2", "\nCode\\n\n")
        self.require_value("code.value_3", "Code\\n")
        self.require_value("code.value_4", "    Code\\n")
        self.require_value(
            "code.value_5",
            'if len(lines) == 3:\n    print(f"{lines}\\n")\nexit(0)',
        )
        self.require_section_map("regex")
        self.require_value("regex.value_1", re.compile(r"^\w+\.[Ee][Ll][Cc][Ll]$"))
        self.require_value("regex.value_2", re.compile("\n^\\w+\\.[Ee][Ll][Cc][Ll]$\n"))
        self.require_value("regex.value_3", re.compile(r"^\w+\.[Ee][Ll][Cc][Ll]$"))
        self.require_value("regex.value_4", re.compile(r"    ^\w+\.[Ee][Ll][Cc][Ll]$"))
        self.require_value("regex.value_5", re.compile("^\\w+\n    \\.[Ee][Ll][Cc][Ll]\n$"))
        self.require_section_map("bytes")
        bytes_value = bytes.fromhex("01 02 03 04 e1 e2 e3 e4")
        self.require_value("bytes.value_1", bytes_value)
        self.require_value("bytes.value_2", bytes_value)
        self.require_value("bytes.value_3", bytes_value)
        self.require_value("bytes.value_4", bytes_value)
        self.require_end()

    def test_sections(self):
        self.setup_from_file("sections.elcl")
        self.require_section_map("main")
        self.require_section_map("main.server.filter")
        self.require_value("main.server.filter.value", "text")
        self.require_section_map("main.client.filter")
        self.require_value("main.client.filter.value", "text")
        self.require_section_map('text."First Text"')
        self.require_value('text."First Text".value', 1)
        self.require_section_map('text."Second Text"')
        self.require_value('text."Second Text".value', 2)
        self.require_end()

    def test_meta(self):
        self.setup_from_file("meta.elcl")
        self.require_meta_value("@signature", "data")
        self.require_meta_value("@version", "1.0")
        self.require_meta_value("@features", "core multi-line time-delta")
        self.require_section_map("main")
        self.require_meta_value("@include", "path1")
        self.require_meta_value("@include", "path2")
        self.require_section_map("second")
        self.require_end()
