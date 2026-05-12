# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev.pre_commit import PreCommitApp
from lib.config import (
    project_relative_posix,
    read_elcl_file,
    utility_source_directory,
    validate_file_suffixes,
    validate_local_names,
    validate_source_relative_path,
)
from lib.error import UtilityError


class ConfigHelpersTest(unittest.TestCase):
    """Tests for shared utility configuration helpers."""

    def test_utility_app_uses_standard_config_file_path(self) -> None:
        self.assertEqual(
            Path(__file__).resolve().parents[1] / "conf" / "pre_commit.elcl",
            PreCommitApp().config_file_path(),
        )

    def test_read_elcl_file_uses_project_src_library(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temp_dir:
            config_file = Path(temp_dir) / "config.elcl"
            config_file.write_text("[main]\nvalue: \"configured\"\n", encoding="utf-8")

            document = read_elcl_file(config_file)

        self.assertEqual("configured", document["main"].get_text("value"))
        self.assertEqual(str(utility_source_directory()), sys.path[0])

    def test_validates_local_names(self) -> None:
        validate_local_names(["file.txt", "directory"], "Names")
        with self.assertRaises(UtilityError):
            validate_local_names(["../file.txt"], "Names")
        with self.assertRaises(UtilityError):
            validate_local_names(["."], "Names")

    def test_validates_file_suffixes(self) -> None:
        validate_file_suffixes([".hpp", ".cpp"], "Suffixes")
        with self.assertRaises(UtilityError):
            validate_file_suffixes(["hpp"], "Suffixes")
        with self.assertRaises(UtilityError):
            validate_file_suffixes(["."], "Suffixes")

    def test_validates_source_relative_paths(self) -> None:
        validate_source_relative_path("src/erbsland", "Path")
        validate_source_relative_path("", "Path")
        with self.assertRaises(UtilityError):
            validate_source_relative_path(".", "Path")
        with self.assertRaises(UtilityError):
            validate_source_relative_path("../src", "Path")
        with self.assertRaises(UtilityError):
            validate_source_relative_path("/tmp/src", "Path")

    def test_project_relative_posix_path(self) -> None:
        project_dir = Path("/tmp/project")

        self.assertEqual("doc/reference", project_relative_posix(project_dir, project_dir / "doc" / "reference"))
        self.assertEqual(
            "doc/reference/",
            project_relative_posix(project_dir, project_dir / "doc" / "reference", is_directory=True),
        )


if __name__ == "__main__":
    unittest.main()
