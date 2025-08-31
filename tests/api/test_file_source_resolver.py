#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
from typing import List

import pytest

from erbsland.conf.error import Error, ConfSyntaxError, ErrorCategory, ConfLimitExceeded
from erbsland.conf.file_source_resolver import FileSourceResolver, ResolverFeature
from erbsland.conf.source import SourceIdentifier
from erbsland.conf.source_resolver import SourceResolverContext
from erbsland.conf.impl import limits


class TestFileSourceResolver:
    """
    Tests for the FileSourceResolver class.

    These tests are adapted from the original C++ tests.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.sources = None
        self.document_source_identifier = None
        self.actual_source_list = []

    def create_test_file(self, path: str, content: str = None) -> Path:
        """
        Create a test file with the given path and content.
        """
        if content is None:
            content = "# Erbsland Configuration Language - Test File\n[main]\nvalue = 123\n"
        path = Path(self.tmp_path) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def create_source_identifier(self, path: Path) -> SourceIdentifier:
        """
        Create a source identifier for the given path.
        """
        canonical_path = path.resolve()
        self.document_source_identifier = SourceIdentifier(SourceIdentifier.FILE, canonical_path.as_posix())
        return self.document_source_identifier

    def setup_file_list(self, file_list: List[str]) -> None:
        """
        Set up a list of test files and create a source identifier for the first one.
        """
        self.document_source_identifier = None
        for path in file_list:
            file_path = self.create_test_file(path)
            if self.document_source_identifier is None:
                self.create_source_identifier(file_path)
        assert self.document_source_identifier is not None

    def expect_success(self, include_text: str, expected: List[str]) -> None:
        """Test that resolving the include text succeeds and returns the expected sources."""
        resolver = FileSourceResolver()
        context = SourceResolverContext(
            include_text,
            self.document_source_identifier,
        )
        self.actual_source_list = []

        try:
            self.sources = resolver.resolve(context)
            # Convert absolute paths to relative paths for comparison
            for source in self.sources:
                source_path = Path(source.identifier.path)
                rel_source_path = source_path.relative_to(self.tmp_path)
                self.actual_source_list.append((rel_source_path.as_posix(), source.identifier.path))
            # Verify the results
            assert len(self.sources) == len(expected)
            for i, source in enumerate(self.sources):
                source_path = Path(source.identifier.path)
                assert source_path.is_absolute()
                rel_source_path = source_path.relative_to(self.tmp_path)
                assert rel_source_path.as_posix() == expected[i]
        except Exception as e:
            # Report a detailed error message
            error_msg = f"Include: {context.include_text}\n"
            error_msg += "Expected Sources:\n"
            for i, source in enumerate(expected):
                error_msg += f"  {i}: {source}\n"
            error_msg += "Actual Sources:\n"
            if not self.actual_source_list:
                error_msg += "  <EMPTY>\n"
            else:
                for i, (rel_path, abs_path) in enumerate(self.actual_source_list):
                    path = rel_path if rel_path else abs_path
                    error_msg += f"  {i}: {path}\n"
            raise AssertionError(error_msg) from e

    def expect_success_variants(self, include_text: str, expected: List[str]) -> None:
        """
        Test various variants of the include text.
        """
        variants = [
            include_text,
            f"file:{include_text}",
            f"{self.tmp_path.as_posix()}/config/{include_text}",
            f"file:{self.tmp_path.as_posix()}/config/{include_text}",
        ]
        for variant in variants:
            self.expect_success(variant, expected)

    def expect_success_abs(self, include_text: str, expected: List[str]) -> None:
        """
        Test with absolute paths.
        """
        abs_include_text = ""
        if include_text.startswith("file:"):
            abs_include_text = "file:"
            include_text = include_text[5:]

        abs_include_text += f"{self.tmp_path}/"
        abs_include_text += include_text

        self.expect_success(abs_include_text, expected)

    def expect_failure(self, include_text: str, expected_error_category: ErrorCategory = ErrorCategory.IO) -> None:
        """
        Test that resolving the include text fails with the expected error category.
        """
        # Skip test if document_source_identifier is not set
        if self.document_source_identifier is None:
            pytest.skip("document_source_identifier is not set")

        resolver = FileSourceResolver()
        context = SourceResolverContext(
            include_text,
            self.document_source_identifier,
        )

        with pytest.raises(Error) as exception_info:
            self.sources = resolver.resolve(context)

        # Check that the error category matches
        assert (
            exception_info.value.category == expected_error_category
        ), f"Expected error category {expected_error_category}, got {exception_info.value.category}"

    def test_incorrect_input(self):
        """
        Test incorrect input to the resolver.
        """
        resolver = FileSourceResolver()

        # Test with empty context
        with pytest.raises(Error):
            resolver.resolve(SourceResolverContext("", None))

        # Test with missing source identifier
        with pytest.raises(Error):
            resolver.resolve(SourceResolverContext("test.elcl", None))

        # Test with text source identifier
        with pytest.raises(Error):
            resolver.resolve(SourceResolverContext("test.elcl", SourceIdentifier(SourceIdentifier.TEXT, "")))

        # Test with a relative path in a source identifier
        with pytest.raises(Error):
            resolver.resolve(
                SourceResolverContext("test.elcl", SourceIdentifier(SourceIdentifier.FILE, "relative.elcl"))
            )

        # Test with a root path in source identifier
        with pytest.raises(Error):
            resolver.resolve(SourceResolverContext("test.elcl", SourceIdentifier(SourceIdentifier.FILE, "/")))

        # Test with an invalid path in a source identifier
        with pytest.raises(Error):
            resolver.resolve(
                SourceResolverContext(
                    "test.elcl", SourceIdentifier(SourceIdentifier.FILE, "/invalid/path/a/b/c/d/e/relative.elcl")
                )
            )

        # Test with a document path that doesn't exist
        with pytest.raises(Error):
            resolver.resolve(
                SourceResolverContext("test.elcl", SourceIdentifier(SourceIdentifier.FILE, "/document.elcl"))
            )

        # Set up a file list for further tests
        file_list = ["config/document.elcl"]
        self.setup_file_list(file_list)

        # Test with a double-file path
        double_file_path = Path(self.tmp_path) / "config/document.elcl/document.elcl"
        with pytest.raises(Error):
            resolver.resolve(
                SourceResolverContext("test.elcl", SourceIdentifier(SourceIdentifier.FILE, double_file_path.as_posix()))
            )

    def test_one_absolute_path(self):
        """
        Test resolving one absolute path.
        """
        # Create test files
        document_path = self.create_test_file("config/document.elcl")
        assert document_path.is_absolute()
        assert document_path.is_file()

        # Create source identifier
        self.create_source_identifier(document_path)
        assert self.document_source_identifier is not None
        assert self.document_source_identifier.name == SourceIdentifier.FILE

        # Create included file
        included_file = self.create_test_file("config/IncludedFile.elcl")
        assert included_file.is_file()

        # Create resolver
        resolver = FileSourceResolver()
        assert resolver is not None

        # Create context with absolute path
        base_path = self.tmp_path.as_posix()
        assert base_path
        context = SourceResolverContext(
            f"{base_path}/config/IncludedFile.elcl",
            self.document_source_identifier,
        )

        # Resolve
        source_list = resolver.resolve(context)
        assert source_list is not None
        assert len(source_list) == 1

        # Check source
        source = source_list[0]
        assert source is not None
        path_from_source_list = source.identifier.path
        actual_path_of_include = included_file.resolve().as_posix()
        assert actual_path_of_include == path_from_source_list

    def test_maximum_wildcards(self):
        """
        Test using the pattern '**/*'.
        """
        # Create test files
        document_path = self.create_test_file("config/document.elcl")
        assert document_path.is_absolute()
        assert document_path.is_file()

        # Create source identifier
        self.create_source_identifier(document_path)
        assert self.document_source_identifier is not None
        assert self.document_source_identifier.name == SourceIdentifier.FILE

        # Create more test files
        self.create_test_file("config/file1.elcl")
        self.create_test_file("config/file2.elcl")
        self.create_test_file("config/file3.elcl")

        # Create resolver
        resolver = FileSourceResolver()
        assert resolver is not None

        # Create context with wildcard pattern
        context = SourceResolverContext(
            "**/*",
            self.document_source_identifier,
        )

        # Resolve
        source_list = resolver.resolve(context)
        assert source_list is not None
        assert len(source_list) == 4  # document.elcl + 3 files

    def test_plain_paths(self):
        """
        Test resolving plain paths.
        """
        file_list = [
            "config/MainDocument.elcl",
            "config/SameDir.elcl",
            "config/SubDir/SubDirDocument.elcl",
            "ParentDocument.elcl",
            "other/OtherDocument.elcl",
        ]
        self.setup_file_list(file_list)

        # Plain and simple
        self.expect_success_variants("SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants("SubDir/SubDirDocument.elcl", ["config/SubDir/SubDirDocument.elcl"])
        self.expect_success_variants("../ParentDocument.elcl", ["ParentDocument.elcl"])
        self.expect_success_variants("../other/OtherDocument.elcl", ["other/OtherDocument.elcl"])
        self.expect_success_variants("..//other//////OtherDocument.elcl", ["other/OtherDocument.elcl"])
        self.expect_success_variants("../////////other///OtherDocument.elcl", ["other/OtherDocument.elcl"])

        # Normalization required
        self.expect_success_variants("./SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants(".//SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants(".\\SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants("./././SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants(".//////./////.///SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants("SubDir/../SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants("SubDir\\..\\.\\SameDir.elcl", ["config/SameDir.elcl"])
        self.expect_success_variants(
            "./SubDir/../../config/SubDir/SubDirDocument.elcl", ["config/SubDir/SubDirDocument.elcl"]
        )
        self.expect_success_variants("../other/../ParentDocument.elcl", ["ParentDocument.elcl"])
        self.expect_success_variants(".\\..\\other\\OtherDocument.elcl", ["other/OtherDocument.elcl"])

    def test_filename_wildcards(self):
        """
        Test resolving paths with filename wildcards.
        """
        file_list = [
            "config/MainDocument.elcl",
            "config/sub/a/doc001.elcl",
            "config/sub/a/doc002.elcl",
            "config/sub/b/doc003.elcl",
            "config/sub/b/doc004.elcl",
            "config/sub/doc005.elcl",
            "config/sub/doc006.elcl",
            "config/sub/conf007.elcl",
            "config/sub/conf008.txt",
            "config/doc009.elcl",
            "config/doc010.elcl",
            "config/doc011.elcl",
            "config/doc012.elcl",
            "doc013.elcl",
            "doc014.elcl",
            "config.txt",
        ]
        self.setup_file_list(file_list)

        # Test with wildcards
        self.expect_success(
            "*",
            [
                "config/MainDocument.elcl",
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success(
            "*.elcl",
            [
                "config/MainDocument.elcl",
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success(
            "doc*",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success(
            "doc*.elcl",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success(
            "../*",
            [
                "config.txt",
                "doc013.elcl",
                "doc014.elcl",
            ],
        )
        self.expect_success(
            "../*4.elcl",
            [
                "doc014.elcl",
            ],
        )
        self.expect_success(
            "../doc*",
            [
                "doc013.elcl",
                "doc014.elcl",
            ],
        )
        self.expect_success(
            "../doc*3.elcl",
            [
                "doc013.elcl",
            ],
        )
        self.expect_success(
            "sub/*",
            [
                "config/sub/conf007.elcl",
                "config/sub/conf008.txt",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success("sub/*4.elcl", [])
        self.expect_success(
            "sub/*.elcl",
            [
                "config/sub/conf007.elcl",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success(
            "sub/d*",
            [
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success(
            "sub/doc00*l",
            [
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

        # Same with absolute paths
        self.expect_success_abs(
            "config/*",
            [
                "config/MainDocument.elcl",
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success_abs(
            "config/*.elcl",
            [
                "config/MainDocument.elcl",
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success_abs(
            "config/doc*",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success_abs(
            "config/doc*.elcl",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
            ],
        )
        self.expect_success_abs(
            "config/../*",
            [
                "config.txt",
                "doc013.elcl",
                "doc014.elcl",
            ],
        )
        self.expect_success_abs(
            "config/../*4.elcl",
            [
                "doc014.elcl",
            ],
        )
        self.expect_success_abs(
            "config/../doc*",
            [
                "doc013.elcl",
                "doc014.elcl",
            ],
        )
        self.expect_success_abs(
            "config/../doc*3.elcl",
            [
                "doc013.elcl",
            ],
        )
        self.expect_success_abs(
            "config/sub/*",
            [
                "config/sub/conf007.elcl",
                "config/sub/conf008.txt",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success_abs("config/sub/*4.elcl", [])
        self.expect_success_abs(
            "config/sub/*.elcl",
            [
                "config/sub/conf007.elcl",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success_abs(
            "config/sub/d*",
            [
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )
        self.expect_success_abs(
            "config/sub/doc00*l",
            [
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

    def test_directory_wildcards(self):
        """
        Test resolving paths with directory wildcards.
        """
        file_list = [
            "config/doc009.elcl",
            "config/doc010.elcl",
            "config/doc011.elcl",
            "config/doc012.elcl",
            "config/main.elcl",
            "config/sub/a/doc001.elcl",
            "config/sub/a/doc002.elcl",
            "config/sub/b/doc003.elcl",
            "config/sub/b/doc004.elcl",
            "config/sub/conf007.elcl",
            "config/sub/conf008.txt",
            "config/sub/doc005.elcl",
            "config/sub/doc006.elcl",
            "config.txt",
            "doc013.elcl",
            "doc014.elcl",
        ]
        self.setup_file_list(file_list)

        # Test with directory wildcards
        self.expect_success(
            "**/*",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
                "config/main.elcl",
                "config/sub/a/doc001.elcl",
                "config/sub/a/doc002.elcl",
                "config/sub/b/doc003.elcl",
                "config/sub/b/doc004.elcl",
                "config/sub/conf007.elcl",
                "config/sub/conf008.txt",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

        # Test with file: protocol
        self.expect_success(
            "file:**/*",
            [
                "config/doc009.elcl",
                "config/doc010.elcl",
                "config/doc011.elcl",
                "config/doc012.elcl",
                "config/main.elcl",
                "config/sub/a/doc001.elcl",
                "config/sub/a/doc002.elcl",
                "config/sub/b/doc003.elcl",
                "config/sub/b/doc004.elcl",
                "config/sub/conf007.elcl",
                "config/sub/conf008.txt",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

        # Test with parent directory
        self.expect_success(
            "../doc*.elcl",
            [
                "doc013.elcl",
                "doc014.elcl",
            ],
        )

        # Test with subdirectory
        self.expect_success(
            "sub/*",
            [
                "config/sub/conf007.elcl",
                "config/sub/conf008.txt",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

        # Test with specific file in subdirectory
        self.expect_success(
            "sub/doc006.elcl",
            [
                "config/sub/doc006.elcl",
            ],
        )

        # Test with non-existent file
        self.expect_success("sub/nonexistent.elcl", [])

        # Test with specific file pattern in subdirectory
        self.expect_success(
            "sub/*.txt",
            [
                "config/sub/conf008.txt",
            ],
        )

        # Test with recursive wildcard for specific file
        self.expect_success(
            "**/doc006.elcl",
            [
                "config/sub/doc006.elcl",
            ],
        )

        # Test with recursive wildcard for file pattern
        self.expect_success(
            "**/*.txt",
            [
                "config/sub/conf008.txt",
            ],
        )

        # Test with recursive wildcard in subdirectory
        self.expect_success(
            "sub/**/*.elcl",
            [
                "config/sub/a/doc001.elcl",
                "config/sub/a/doc002.elcl",
                "config/sub/b/doc003.elcl",
                "config/sub/b/doc004.elcl",
                "config/sub/conf007.elcl",
                "config/sub/doc005.elcl",
                "config/sub/doc006.elcl",
            ],
        )

    def test_errors(self):
        """Test error cases."""
        file_list = [
            "config/MainDocument.elcl",
            "config/SameDir.elcl",
            "config/SubDir/SubDirDocument.elcl",
            "config/SubDir/A/a.elcl",
            "config/SubDir/B/b.elcl",
            "ParentDocument.elcl",
            "other/OtherDocument.elcl",
        ]
        self.setup_file_list(file_list)

        # Test empty path
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("", self.document_source_identifier))

        # Test path ending with separator
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("SameDir.elcl/", self.document_source_identifier))

        # Test invalid wildcards in directory
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("Sub*Dir/SubDirDocument.elcl", self.document_source_identifier))

        # Test multiple wildcards in filename
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("SubDir/S*D*Document.elcl", self.document_source_identifier))

        # Test invalid recursive wildcards
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("**/**/SubDirDocument.elcl", self.document_source_identifier))

        # Test invalid UNC paths
        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("//", self.document_source_identifier))

        with pytest.raises(Error):
            resolver = FileSourceResolver()
            resolver.resolve(SourceResolverContext("///", self.document_source_identifier))

    def test_source_path_cannot_be_canonicalized(self, monkeypatch):
        """Fail if the source path cannot be canonicalized."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)

        include_dir = Path(self.tmp_path) / "config/sub"
        include_dir.mkdir(parents=True, exist_ok=True)
        (include_dir / "include.elcl").write_text("test")

        real_resolve = Path.resolve

        def mock_resolve(self, *args, **kwargs):
            if self == include_dir:
                raise OSError("mock canonicalization failure")
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", mock_resolve)

        resolver = FileSourceResolver()
        with pytest.raises(Error) as exc_info:
            resolver.resolve(SourceResolverContext("sub/include.elcl", self.document_source_identifier))
        assert exc_info.value.category == ErrorCategory.SYNTAX

    def test_parent_path_cannot_be_canonicalized(self, monkeypatch):
        """Fail if the parent document path cannot be canonicalized."""
        document_path = self.create_test_file("config/document.elcl")
        canonical_doc = document_path.resolve()
        self.create_source_identifier(document_path)

        real_resolve = Path.resolve

        def mock_resolve(self, *args, **kwargs):
            if self == canonical_doc:
                raise OSError("mock canonicalization failure")
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", mock_resolve)

        resolver = FileSourceResolver()
        with pytest.raises(Error) as exc_info:
            resolver.resolve(SourceResolverContext("SameDir.elcl", self.document_source_identifier))
        assert exc_info.value.category == ErrorCategory.SYNTAX

    def test_parent_path_points_to_file(self):
        """Parent of the document path is a file, which should raise an error."""
        parent_file = self.create_test_file("path/file.txt")
        fictive_doc = parent_file / "main.elcl"
        source_identifier = SourceIdentifier(SourceIdentifier.FILE, fictive_doc.as_posix())
        resolver = FileSourceResolver()
        with pytest.raises(Error) as exc_info:
            resolver.resolve(SourceResolverContext("test.elcl", source_identifier))
        assert exc_info.value.category == ErrorCategory.SYNTAX

    def test_absolute_path_without_feature(self):
        """Absolute paths are rejected when the ABSOLUTE_PATHS feature is disabled."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        included_file = self.create_test_file("other/abs.elcl")

        resolver = FileSourceResolver(features=ResolverFeature.ALL & ~ResolverFeature.ABSOLUTE_PATHS)
        abs_path = included_file.resolve().as_posix()
        with pytest.raises(Error) as exc_info:
            resolver.resolve(SourceResolverContext(abs_path, self.document_source_identifier))
        assert exc_info.value.category == ErrorCategory.SYNTAX

    def test_include_path_too_long(self):
        """An include text exceeding 500 characters must raise a SyntaxError."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        resolver = FileSourceResolver()
        long_include = "a" * 501
        with pytest.raises(ConfSyntaxError):
            resolver.resolve(SourceResolverContext(long_include, self.document_source_identifier))

    def test_filename_wildcard_not_enabled(self):
        """A filename wildcard requires the FILENAME_WILDCARD feature."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        resolver = FileSourceResolver(ResolverFeature.ALL & ~ResolverFeature.FILENAME_WILDCARD)
        with pytest.raises(ConfSyntaxError):
            resolver.resolve(SourceResolverContext("*.elcl", self.document_source_identifier))

    def test_recursive_wildcard_not_enabled(self):
        """A recursive wildcard requires the RECURSIVE_WILDCARD feature."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        resolver = FileSourceResolver(ResolverFeature.ALL & ~ResolverFeature.RECURSIVE_WILDCARD)
        with pytest.raises(ConfSyntaxError):
            resolver.resolve(SourceResolverContext("**/*.elcl", self.document_source_identifier))

    def test_include_limit_exceeded(self, monkeypatch):
        """Including more sources than allowed must raise ConfLimitExceeded."""
        self.setup_file_list(
            [
                "config/document.elcl",
                "config/one.elcl",
                "config/two.elcl",
            ]
        )
        monkeypatch.setattr(limits, "MAX_INCLUDE_SOURCES", 1)
        resolver = FileSourceResolver()
        context = SourceResolverContext("*.elcl", self.document_source_identifier)
        with pytest.raises(ConfLimitExceeded):
            resolver.resolve(context)

    def test_invalid_protocol_prefix(self):
        """Non 'file:' prefixes must raise a SyntaxError if FILE_PROTOCOL feature is enabled."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        resolver = FileSourceResolver()
        with pytest.raises(ConfSyntaxError):
            resolver.resolve(SourceResolverContext("http:foo.elcl", self.document_source_identifier))

    def test_unc_path_double_slashes(self):
        """Double slashes in UNC paths should be normalized."""
        resolver = FileSourceResolver()
        path = "//server//share///dir//file.elcl"
        normalized = resolver._normalize_path_separators(path)
        assert normalized == "//server/share/dir/file.elcl"

    def test_unc_path_invalid_host(self):
        """Invalid characters in UNC host part must raise SyntaxError."""
        resolver = FileSourceResolver()
        with pytest.raises(ConfSyntaxError):
            resolver._normalize_path_separators("//inva|lid/share/file.elcl")

    def test_file_protocol_feature_disabled(self):
        """Resolver should ignore plain paths but reject the 'file:' prefix when the feature is disabled."""
        document_path = self.create_test_file("config/document.elcl")
        target_path = self.create_test_file("config/other.elcl")
        self.create_source_identifier(document_path)
        resolver = FileSourceResolver(ResolverFeature.ALL & ~ResolverFeature.FILE_PROTOCOL)

        # Plain include succeeds and returns the expected path
        context = SourceResolverContext("other.elcl", self.document_source_identifier)
        sources = resolver.resolve(context)
        assert Path(sources[0].identifier.path).resolve() == target_path.resolve()

        # 'file:' prefix must raise a syntax error
        with pytest.raises(ConfSyntaxError):
            resolver.resolve(SourceResolverContext("file:other.elcl", self.document_source_identifier))

    def test_get_base_directory_parent_not_directory(self, monkeypatch):
        """_get_base_directory must fail if the parent path is not a directory."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        parent_path = document_path.parent.resolve()
        resolver = FileSourceResolver()

        original_is_dir = Path.is_dir

        def fake_is_dir(self: Path) -> bool:  # noqa: N802 - Pytest patching
            if self == parent_path:
                return False
            return original_is_dir(self)

        monkeypatch.setattr(Path, "is_dir", fake_is_dir)

        with pytest.raises(ConfSyntaxError):
            resolver._get_base_directory(self.document_source_identifier)

    @pytest.mark.parametrize(
        "directory, prepare, message",
        [
            pytest.param("missing", lambda self: None, "does not exist", id="missing-directory"),
            pytest.param(
                "notdir", lambda self: self.create_test_file("notdir"), "not a directory", id="not-a-directory"
            ),
        ],
    )
    def test_build_directory_invalid(self, directory, prepare, message):
        """_build_directory must fail if the base directory is invalid."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        prepare(self)
        resolver = FileSourceResolver()

        with pytest.raises(ConfSyntaxError) as exc_info:
            resolver._build_directory(self.document_source_identifier, str(self.tmp_path / directory))
        assert message in str(exc_info.value)

    def test_build_directory_canonicalization_error(self, monkeypatch):
        """_build_directory must report the system error if canonicalization fails."""
        document_path = self.create_test_file("config/document.elcl")
        self.create_source_identifier(document_path)
        directory_path = self.tmp_path / "config"
        resolver = FileSourceResolver()

        original_resolve = Path.resolve

        def fake_resolve(self: Path, *args, **kwargs):  # noqa: N802 - Pytest patching
            if self == directory_path:
                raise OSError("boom")
            return original_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", fake_resolve)

        with pytest.raises(ConfSyntaxError) as exc_info:
            resolver._build_directory(self.document_source_identifier, directory_path.as_posix())
        assert "Could not canonicalize the base directory of an include path." in str(exc_info.value)
        assert exc_info.value.system_message == "boom"
