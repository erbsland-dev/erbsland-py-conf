#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from erbsland.conf.access_check import AccessCheckResult, AccessSources
from erbsland.conf.error import ConfAccessError, Error
from erbsland.conf.file_access_check import AccessFeature, FileAccessCheck
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.impl import limits


def make_sources(
    src: Path, parent: Path | None, *, root: Path | None = None, src_name: str = SourceIdentifier.FILE
) -> AccessSources:
    source = SourceIdentifier(src_name, str(src))
    parent_id = SourceIdentifier(SourceIdentifier.FILE, str(parent)) if parent else None
    root_id = SourceIdentifier(SourceIdentifier.FILE, str(root if root else (parent if parent else src)))
    return AccessSources(source=source, parent=parent_id, root=root_id)


class TestFileAccessCheck:
    def test_non_source_identifier_denied(self):
        check = FileAccessCheck()
        root = SourceIdentifier(SourceIdentifier.FILE, "root")
        sources = AccessSources(source="notidentifier", parent=None, root=root)  # type: ignore[arg-type]
        assert check.check(sources) is AccessCheckResult.DENIED

    @pytest.mark.parametrize(
        "source,parent,root",
        [
            pytest.param(
                SourceIdentifier(SourceIdentifier.FILE, "root.elcl"),
                SourceIdentifier(SourceIdentifier.FILE, "parent.elcl"),
                SourceIdentifier(SourceIdentifier.FILE, "root.elcl"),
                id="source_is_root",
            ),
            pytest.param(
                SourceIdentifier(SourceIdentifier.FILE, "child.elcl"),
                None,
                SourceIdentifier(SourceIdentifier.FILE, "root.elcl"),
                id="no_parent",
            ),
        ],
    )
    def test_root_or_no_parent_grants_access(self, source, parent, root):
        check = FileAccessCheck()
        assert check.check(AccessSources(source=source, parent=parent, root=root)) is AccessCheckResult.GRANTED

    def test_non_file_source_allowed_when_only_file_sources_disabled(self):
        check = FileAccessCheck()
        src = SourceIdentifier(SourceIdentifier.TEXT, "inline")
        parent = SourceIdentifier(SourceIdentifier.FILE, "parent.elcl")
        root = parent
        assert check.check(AccessSources(source=src, parent=parent, root=root)) is AccessCheckResult.GRANTED

    def test_non_file_source_rejected_when_only_file_sources_enabled(self):
        check = FileAccessCheck(AccessFeature.ONLY_FILE_SOURCES)
        src = SourceIdentifier(SourceIdentifier.TEXT, "inline")
        parent = SourceIdentifier(SourceIdentifier.FILE, "parent.elcl")
        root = parent
        with pytest.raises(ConfAccessError):
            check.check(AccessSources(source=src, parent=parent, root=root))

    def test_parent_path_not_found(self, tmp_path):
        missing_parent = tmp_path / "missing" / "parent.elcl"
        src = tmp_path / "child.elcl"
        check = FileAccessCheck()
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, missing_parent, root=missing_parent))

    def test_parent_not_directory_error(self, tmp_path, monkeypatch):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.elcl"
        original_is_dir = Path.is_dir

        def fake_is_dir(self):
            if self == tmp_path:
                return False
            return original_is_dir(self)

        monkeypatch.setattr(Path, "is_dir", fake_is_dir)
        check = FileAccessCheck()
        with pytest.raises(Error):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_source_path_not_found(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        missing = tmp_path / "missing.elcl"
        check = FileAccessCheck()
        with pytest.raises(Error):
            check.check(make_sources(missing, parent_file, root=parent_file))

    def test_file_size_limit_exceeded(self, tmp_path, monkeypatch):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.elcl"
        src.write_bytes(b"0123456789")
        monkeypatch.setattr(limits, "MAX_DOCUMENT_SIZE", 1)
        check = FileAccessCheck()
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_require_suffix_rejects_wrong_extension(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.txt"
        src.touch()
        check = FileAccessCheck(AccessFeature.DEFAULTS | AccessFeature.REQUIRE_SUFFIX)
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_require_suffix_allows_correct_extension(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.elcl"
        src.touch()
        check = FileAccessCheck(AccessFeature.DEFAULTS | AccessFeature.REQUIRE_SUFFIX)
        assert check.check(make_sources(src, parent_file, root=parent_file)) is AccessCheckResult.GRANTED

    def test_any_directory_allows_outside_files(self, tmp_path):
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        parent_file = parent_dir / "parent.elcl"
        parent_file.touch()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        src = outside_dir / "child.elcl"
        src.touch()
        check = FileAccessCheck(AccessFeature.ANY_DIRECTORY | AccessFeature.LIMIT_SIZE)
        assert check.check(make_sources(src, parent_file, root=parent_file)) is AccessCheckResult.GRANTED

    def test_same_directory_rejected_without_flag(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.elcl"
        src.touch()
        features = AccessFeature.DEFAULTS & ~AccessFeature.SAME_DIRECTORY
        check = FileAccessCheck(features)
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_subdirectory_rejected_without_flag(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        subdir = tmp_path / "sub"
        subdir.mkdir()
        src = subdir / "child.elcl"
        src.touch()
        features = AccessFeature.DEFAULTS & ~AccessFeature.SUBDIRECTORIES
        check = FileAccessCheck(features)
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_outside_parent_directory_rejected(self, tmp_path):
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        parent_file = parent_dir / "parent.elcl"
        parent_file.touch()
        outside = tmp_path / "outside"
        outside.mkdir()
        src = outside / "child.elcl"
        src.touch()
        check = FileAccessCheck()
        with pytest.raises(ConfAccessError):
            check.check(make_sources(src, parent_file, root=parent_file))

    def test_valid_same_directory(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        src = tmp_path / "child.elcl"
        src.touch()
        check = FileAccessCheck()
        assert check.check(make_sources(src, parent_file, root=parent_file)) is AccessCheckResult.GRANTED

    def test_valid_subdirectory(self, tmp_path):
        parent_file = tmp_path / "parent.elcl"
        parent_file.touch()
        subdir = tmp_path / "sub"
        subdir.mkdir()
        src = subdir / "child.elcl"
        src.touch()
        check = FileAccessCheck()
        assert check.check(make_sources(src, parent_file, root=parent_file)) is AccessCheckResult.GRANTED

    def test_access_feature_repr(self):
        assert repr(AccessFeature.SAME_DIRECTORY) == "SAME_DIRECTORY"
