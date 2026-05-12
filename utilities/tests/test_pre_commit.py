# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev.pre_commit import PreCommitApp
from lib.error import UtilityError


class PreCommitTest(unittest.TestCase):
    """Tests for pre-commit behavior."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.project_dir = Path(self.temp_dir.name)
        self.run_git("init")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "Pre Commit Test")
        self.run_git("config", "commit.gpgsign", "false")
        (self.project_dir / "file.txt").write_text("initial\n", encoding="utf-8")
        self.run_git("add", "file.txt")
        self.run_git("commit", "-m", "initial")
        self.app = PreCommitApp()
        self.app.project_root = self.project_dir
        self.app.black_source_directory = self.project_dir / "src"
        self.app.black_source_directory.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_git(self, *args: str) -> None:
        """Run git in the temporary project."""
        subprocess.run(
            ["git", "-C", str(self.project_dir), *args],
            check=True,
            capture_output=True,
        )

    def test_run_black_uses_python_module_and_source_directory(self) -> None:
        with patch("dev.pre_commit.subprocess.run") as mock_run:
            self.app.run_black()

        mock_run.assert_called_once()
        self.assertEqual(
            [sys.executable, "-m", "black", str(self.app.black_source_directory)],
            mock_run.call_args.args[0],
        )
        self.assertTrue(mock_run.call_args.kwargs["check"])

    def test_git_state_detects_dirty_file_content_changes(self) -> None:
        (self.project_dir / "file.txt").write_text("dirty once\n", encoding="utf-8")
        initial_state = self.app.git_local_state()

        (self.project_dir / "file.txt").write_text("dirty twice\n", encoding="utf-8")

        with self.assertRaises(UtilityError):
            self.app.require_unchanged_git_state(initial_state)

    def test_git_state_detects_untracked_file_content_changes(self) -> None:
        (self.project_dir / "generated.txt").write_text("generated once\n", encoding="utf-8")
        initial_state = self.app.git_local_state()

        (self.project_dir / "generated.txt").write_text("generated twice\n", encoding="utf-8")

        with self.assertRaises(UtilityError):
            self.app.require_unchanged_git_state(initial_state)

    def test_git_state_accepts_unchanged_dirty_state(self) -> None:
        (self.project_dir / "file.txt").write_text("dirty once\n", encoding="utf-8")
        initial_state = self.app.git_local_state()

        self.app.require_unchanged_git_state(initial_state)


if __name__ == "__main__":
    unittest.main()
