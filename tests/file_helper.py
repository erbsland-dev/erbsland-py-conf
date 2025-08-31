#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
from pathlib import Path


from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.text_source import TextSource


class FileHelper:
    def __init__(self, temp_path: Path):
        self.temp_path = temp_path

    def create_file_source(self, content: str | bytes, name: str = "main.elcl") -> FileSource:
        file_path = self.temp_path / name
        if isinstance(content, str):
            file_path.write_bytes(content.encode("utf-8"))
        else:
            file_path.write_bytes(content)
        return FileSource(file_path)

    def create_text_source(self, content: str | bytes) -> TextSource:
        if isinstance(content, str):
            return TextSource(content)
        return TextSource(content.decode("utf-8"))

    def create_file_and_text_source(
        self, content: str | bytes, name: str = "main.elcl"
    ) -> tuple[FileSource, TextSource]:
        file_source = self.create_file_source(content, name)
        text_source = self.create_text_source(content)
        return file_source, text_source
