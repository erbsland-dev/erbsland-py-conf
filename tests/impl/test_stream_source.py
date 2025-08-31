#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from ..file_helper import FileHelper

from erbsland.conf.error import ConfEncodingError, ConfLimitExceeded
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.limits import MAX_LINE_LENGTH
from erbsland.conf.impl.text_source import TextSource


def _read_all_lines(source):
    source.open()
    lines = []
    try:
        while True:
            line = source.readline()
            if line == "":
                break
            lines.append(line)
    finally:
        source.close()
    return lines


class TestStreamSourceLineLimits:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.file_helper = FileHelper(tmp_path)

    def _test_file_and_text_succeed(self, file_content: str | bytes, expected_lines: list[str]):
        file_source = self.file_helper.create_file_source(file_content)
        assert _read_all_lines(file_source) == expected_lines
        text_source = self.file_helper.create_text_source(file_content)
        assert _read_all_lines(text_source) == expected_lines

    def test_zero_length_text_and_file(self):
        self._test_file_and_text_succeed("", [])

    def test_line_length_exceeded(self):
        valid_line = b"a" * (MAX_LINE_LENGTH - 1) + b"\n"
        invalid_line = b"b" * MAX_LINE_LENGTH + b"\n"
        content = valid_line + invalid_line
        for source in self.file_helper.create_file_and_text_source(content):
            source.open()
            assert source.readline() == valid_line.decode()
            with pytest.raises(ConfLimitExceeded):
                source.readline()
            source.close()

    def test_mixed_line_endings(self):
        data = b"line1\nline2\r\nline3"
        self._test_file_and_text_succeed(
            data,
            [
                "line1\n",
                "line2\r\n",
                "line3",
            ],
        )
        data2 = b"lineA\r\nlineB\n"
        self._test_file_and_text_succeed(
            data2,
            [
                "lineA\r\n",
                "lineB\n",
            ],
        )


class TestStreamSourceEncodingErrors:
    @pytest.mark.parametrize(
        "content",
        [
            pytest.param(bytes.fromhex("41 42 43 80 41 42"), id="lone-continuation-0x80"),
            pytest.param(bytes.fromhex("41 42 43 87 41 42"), id="lone-continuation-0x87"),
            pytest.param(bytes.fromhex("41 42 43 91 41 42"), id="lone-continuation-0x91"),
            pytest.param(bytes.fromhex("41 42 43 AF 41 42"), id="lone-continuation-0xAF"),
            pytest.param(bytes.fromhex("41 42 43 BF 41 42"), id="lone-continuation-0xBF"),
            pytest.param(bytes.fromhex("20 ED A0 80 40"), id="surrogate-U+D800-ED-A0-80"),
            pytest.param(bytes.fromhex("40 41 42 43 ED BF BF 40 41 42"), id="surrogate-U+DFFF-ED-BF-BF"),
            pytest.param(bytes.fromhex("41 F4 90 80 80 41"), id=">U+10FFFF-F4-90-80-80"),
            pytest.param(bytes.fromhex("41 F5 90 80 80 80 41"), id="forbidden-5-byte-seq-start-F5"),
            pytest.param(bytes.fromhex("41 F6 90 80 80 80 80 41"), id="forbidden-6-byte-seq-start-F6"),
            pytest.param(bytes.fromhex("41 F7 90 80 80 80 80 80 41"), id="forbidden-7-byte-seq-start-F7"),
            pytest.param(bytes.fromhex("41 F8 90 80 80 80 80 80 80 41"), id="forbidden-8-byte-seq-start-F8"),
            pytest.param(bytes.fromhex("41 F9 90 80 80 80 80 80 80 80 41"), id="forbidden-9-byte-seq-start-F9"),
            pytest.param(bytes.fromhex("41 FA 90 80 80 80 80 80 80 80 80 41"), id="forbidden-10-byte-seq-start-FA"),
            pytest.param(bytes.fromhex("41 FB 90 80 80 80 80 80 80 80 80 80 41"), id="forbidden-11-byte-seq-start-FB"),
            pytest.param(
                bytes.fromhex("41 FC 90 80 80 80 80 80 80 80 80 80 80 41"), id="forbidden-12-byte-seq-start-FC"
            ),
            pytest.param(
                bytes.fromhex("41 FD 90 80 80 80 80 80 80 80 80 80 80 80 41"), id="forbidden-13-byte-seq-start-FD"
            ),
            pytest.param(bytes.fromhex("41 42 43 C0 80 41 42"), id="overlong-NUL-C0-80"),
            pytest.param(bytes.fromhex("41 42 43 C1 80 41 42"), id="overlong-ASCII-0x40-C1-80"),
            pytest.param(bytes.fromhex("41 42 43 E0 9F BF 41 42"), id="overlong-3-byte-E0-9F-BF"),
            pytest.param(bytes.fromhex("41 42 43 F0 8F BF BF 41 42"), id="overlong-4-byte-F0-8F-BF-BF"),
            pytest.param(bytes.fromhex("41 42 C2 41 42"), id="truncated-2-byte-lead-C2"),
            pytest.param(bytes.fromhex("41 42 E0 80 41 42"), id="truncated/invalid-3-byte-lead-E0"),
            pytest.param(bytes.fromhex("41 42 F0 80 80 41 42"), id="truncated/invalid-4-byte-lead-F0"),
        ],
    )
    def test_invalid_utf8_sequence(self, tmp_path, content):
        file_path = tmp_path / "invalid.elcl"
        file_path.write_bytes(content)
        source = FileSource(file_path)
        source.open()
        with pytest.raises(ConfEncodingError):
            source.readline()
        source.close()
