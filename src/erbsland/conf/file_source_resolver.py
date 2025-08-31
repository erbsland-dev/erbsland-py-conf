#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


"""Resolver for ``file:`` include directives."""

import re
from enum import Flag, auto
from pathlib import Path
from typing import List, Tuple

from erbsland.conf.error import Error, ConfSyntaxError, ConfLimitExceeded
from erbsland.conf.impl import limits
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.source import Source, SourceIdentifier
from erbsland.conf.source_resolver import SourceResolver, SourceResolverContext


class ResolverFeature(Flag):
    """Features supported by the file source resolver."""

    RECURSIVE_WILDCARD = auto()
    """
    Support the recursive wildcard ``**`` in the directory part of a path. If this feature is disabled,
    recursive wildcards are rejected.
    """
    FILENAME_WILDCARD = auto()
    """Support the filename wildcard ``*``. If this feature is disabled, wildcards in the filename are rejected."""
    ABSOLUTE_PATHS = auto()
    """Support absolute include paths. If this feature is disabled, absolute paths are rejected."""
    WINDOWS_UNC_PATH = auto()
    """Support Windows UNC paths. If this feature is disabled, UNC paths are rejected."""
    FILE_PROTOCOL = auto()
    """
    Support the ``file:`` protocol prefix. If this feature is disabled, paths containing a protocol prefix are
    rejected.
    """
    ALL = RECURSIVE_WILDCARD | FILENAME_WILDCARD | ABSOLUTE_PATHS | WINDOWS_UNC_PATH | FILE_PROTOCOL
    """All features."""


class FileSourceResolver(SourceResolver):
    """
    Resolve ``@include`` statements referencing local files.

    The resolver supports relative and absolute paths and provides optional wildcard support.

    Examples:

    .. code-block:: erbsland-conf

        @include: "file:example.elcl"          # File in the same directory
        @include: "file:sub/example.elcl"      # File in a subdirectory
        @include: "file:/usr/local/example.elcl" # Absolute path
    """

    def __init__(self, features: ResolverFeature = ResolverFeature.ALL):
        """
        Initialize the resolver.

        :param features: Feature flags to enable, defaults to ``ResolverFeature.ALL``.
        """

        self._features = features

    def resolve(self, context: SourceResolverContext) -> list[Source]:
        """Resolve the include path from *context*.

        :param context: Resolution context containing the include text and source.
        :return: A list of resolved file sources.
        :raises ConfSyntaxError: If the include text is invalid.
        :raises ConfLimitExceeded: If the include matches more documents than allowed.
        """
        try:
            # An empty include text is not valid.
            if not context.include_text:
                raise ConfSyntaxError("The include path is empty", source=context.source)

            # It makes no sense for having more than 500 characters.
            if len(context.include_text) > 500:
                raise ConfSyntaxError("The include path is too long", source=context.source)

            path_string = context.include_text
            path_string = self._remove_file_protocol(path_string)
            path_string = self._normalize_path_separators(path_string)

            directory, filename = self._split_directory_and_filename(path_string)
            filename_pattern, has_wildcard = self._get_filename_pattern(filename)

            if has_wildcard and ResolverFeature.FILENAME_WILDCARD not in self._features:
                raise ConfSyntaxError("The filename wildcard '*' is not supported", source=context.source)

            directory, is_recursive = self._validate_directory_wildcard(directory)

            if is_recursive and ResolverFeature.RECURSIVE_WILDCARD not in self._features:
                raise ConfSyntaxError(
                    "The recursive wildcard '**' is not supported",
                    source=context.source,
                )

            directory_path = self._build_directory(context.source, directory)
            paths = self._scan_for_paths(directory_path, is_recursive, filename_pattern)

            return [FileSource(path) for path in paths]
        except Exception as e:
            if isinstance(e, Error):
                raise e
            raise ConfSyntaxError(
                f"An unexpected error prevents resolving this include pattern: {str(e)}",
                source=context.source,
            )

    def _remove_file_protocol(self, path: str) -> str:
        """
        Remove the ``file:`` protocol prefix from *path*.

        :param path: The path to process.
        :return: The path without the protocol prefix.
        :raises ConfSyntaxError: If another protocol prefix is used or ``file:`` is disabled.
        """
        if ResolverFeature.FILE_PROTOCOL in self._features:
            if path.startswith("file:"):
                return path[5:]
            # Detect other protocol prefixes but ignore Windows drive letters
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path) and not re.match(r"^[A-Za-z]:", path):
                raise ConfSyntaxError("Only the 'file:' protocol prefix is supported")
            return path
        else:
            if path.startswith("file:"):
                raise ConfSyntaxError("File protocol prefix 'file:' is not supported")
            return path

    def _normalize_path_separators(self, path: str) -> str:
        """Normalize path separators, collapse duplicates and validate UNC paths."""
        path = path.replace("\\", "/")
        if ResolverFeature.WINDOWS_UNC_PATH in self._features and path.startswith("//"):
            path = "//" + re.sub("/+", "/", path[2:])
            self._verify_unc_path(path)
        else:
            path = re.sub("/+", "/", path)
        if path.endswith("/"):
            raise ConfSyntaxError("An include path must not end with a path separator")
        return path

    def _verify_unc_path(self, path: str) -> None:
        """Verify that *path* is a valid Windows UNC path."""
        if not re.match(r'//[^/<>:"|?*]+/[^/]+', path):
            raise ConfSyntaxError("Invalid Windows UNC path")

    def _split_directory_and_filename(self, path: str) -> Tuple[str, str]:
        """Split *path* into its directory and filename components."""
        return tuple(path.rsplit("/", 1)) if "/" in path else ("", path)

    def _get_filename_pattern(self, filename: str) -> tuple[str, bool]:
        """Return the filename pattern and whether it contains a wildcard."""
        if not re.fullmatch(r"[^*]*\*?[^*]*", filename):
            raise ConfSyntaxError("Invalid wildcard in filename")
        return filename, "*" in filename

    def _validate_directory_wildcard(self, directory: str) -> Tuple[str, bool]:
        """Return the directory without wildcards and flag whether it is recursive."""
        if not directory:
            return "", False
        match = re.fullmatch(r"(?:(?P<prefix>[^*]*(?:/[^*]+)*)/)?\*\*", directory)
        if match:
            return match.group("prefix") or "", True
        if "*" in directory:
            raise ConfSyntaxError("Invalid wildcard in directory")
        return directory, False

    def _get_base_directory(self, source_identifier: SourceIdentifier) -> Path:
        """
        Get the base directory from the source identifier.

        :param source_identifier: The source identifier.
        :return: The base directory.
        """
        if source_identifier is None:
            raise ValueError("'source_identifier' must not be None")

        error_prefix = "Cannot determine the base directory of the including document. "

        if source_identifier.name != SourceIdentifier.FILE:
            raise ConfSyntaxError(
                error_prefix + "The document is not a file source.",
                source=source_identifier,
            )

        result = Path(source_identifier.path)

        if not result.is_absolute():
            raise ConfSyntaxError(
                error_prefix + "The path of the document is not absolute.",
                path=result,
                source=source_identifier,
            )

        if not result.exists():
            raise ConfSyntaxError(
                error_prefix + "The path of the document does not exist.",
                path=result,
                source=source_identifier,
            )
        if not result.is_file():
            raise ConfSyntaxError(
                error_prefix + "The path of the document is not a file.",
                path=result,
                source=source_identifier,
            )

        try:
            result = result.resolve()
        except Exception as e:
            raise ConfSyntaxError(
                error_prefix + "The path of the document cannot be canonicalized.",
                path=result,
                source=source_identifier,
                system_message=str(e),
            )

        base_directory = result.parent

        if not base_directory.is_dir():
            raise ConfSyntaxError(
                error_prefix + "The parent path of the document is not a directory.",
                path=base_directory,
                source=source_identifier,
            )

        return base_directory

    def _build_directory(self, source_identifier: SourceIdentifier, directory: str) -> Path:
        """
        Build the directory path.

        :param source_identifier: The source identifier.
        :param directory: The directory string.
        :return: The directory path.
        """
        if not directory:
            result = self._get_base_directory(source_identifier)
        else:
            result = Path(directory)
            if not result.is_absolute():
                result = self._get_base_directory(source_identifier) / result
            elif ResolverFeature.ABSOLUTE_PATHS not in self._features:
                raise ConfSyntaxError("Absolute include paths are not allowed", source=source_identifier)

        try:
            if not result.exists():
                raise ConfSyntaxError(
                    "The base directory of an include path does not exist",
                    path=result,
                    source=source_identifier,
                )

            result = result.resolve()

            if not result.is_dir():
                raise ConfSyntaxError(
                    "The base of an include path is not a directory",
                    path=result,
                    source=source_identifier,
                )
        except Exception as e:
            raise ConfSyntaxError(
                "Could not canonicalize the base directory of an include path.",
                path=result,
                source=source_identifier,
                system_message=str(e),
            )

        return result

    def _scan_for_paths(self, directory: Path, is_recursive: bool, filename_pattern: str) -> List[Path]:
        """
        Scan for paths matching the pattern.

        :param directory: The directory to scan.
        :param is_recursive: Whether to scan recursively.
        :param filename_pattern: The filename pattern.
        :return: A list of matching paths.
        """
        paths: List[Path] = []
        iterator = directory.rglob(filename_pattern) if is_recursive else directory.glob(filename_pattern)
        for path in iterator:
            if not path.is_file():
                continue
            if len(paths) >= limits.MAX_INCLUDE_SOURCES:
                raise ConfLimitExceeded(
                    f"This include directive includes more than {limits.MAX_INCLUDE_SOURCES} documents",
                )
            paths.append(path)

        # Sort paths to ensure a deterministic order
        paths.sort()
        return paths
