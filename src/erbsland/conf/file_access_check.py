#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from enum import auto, IntFlag
from pathlib import Path

from erbsland.conf.access_check import AccessCheck, AccessSources, AccessCheckResult
from erbsland.conf.error import Error, ConfAccessError, ErrorCategory
from erbsland.conf.impl import limits
from erbsland.conf.source import SourceIdentifier


class AccessFeature(IntFlag):
    """
    Feature flags controlling file access restrictions.

    The default configuration enables
    :data:`~erbsland.conf.access_check.AccessFeatures.SAME_DIRECTORY`,
    :data:`~erbsland.conf.access_check.AccessFeatures.SUBDIRECTORIES`, and
    :data:`~erbsland.conf.access_check.AccessFeatures.LIMIT_SIZE`.

    *   If none of :data:`~AccessFeatures.SAME_DIRECTORY`,
        :data:`~erbsland.conf.access_check.AccessFeatures.SUBDIRECTORIES` or
        :data:`~erbsland.conf.access_check.AccessFeatures.ANY_DIRECTORY` is set, all file sources are rejected.
    *   If a file is included from a non-file source and
        :data:`~erbsland.conf.access_check.AccessFeatures.ANY_DIRECTORY` is not enabled, the source is rejected.
    """

    SAME_DIRECTORY = auto()
    """
    Allow included sources to be in the same directory as the including document (recommended, default).
    Example: If the including document has the path ``config/main.elcl``, documents such as
    ``config/other.elcl`` are accepted. If disabled, such documents are rejected.
    """

    SUBDIRECTORIES = auto()
    """
    Allow included sources in subdirectories of the including document (recommended, default).
    Example: If the including document is ``config/main.elcl``, documents like ``config/sub/other.elcl``
    are accepted. If disabled, subdirectory documents are rejected.
    """

    ANY_DIRECTORY = auto()
    """Allow included sources in any directory, including unrelated paths or remote shares. **Not recommended**."""

    ONLY_FILE_SOURCES = auto()
    """
    When enabled, only file-based sources are accepted. Sources of other types (for example, ``text``) are
    rejected. When disabled (default), non-file sources are automatically accepted, which allows chaining
    other checks.
    """

    LIMIT_SIZE = auto()
    """Limit file size to a maximum of 100 MB (recommended, default)."""

    REQUIRE_SUFFIX = auto()
    """Only allow file sources with an ``.elcl`` suffix."""

    DEFAULTS = SAME_DIRECTORY | SUBDIRECTORIES | LIMIT_SIZE
    """Default set of enabled features."""

    def __repr__(self) -> str:
        return f"{self.name}"  # pragma: no cover


class FileAccessCheck(AccessCheck):
    """Access check implementation for file-based sources."""

    def __init__(self, features: AccessFeature = AccessFeature.DEFAULTS):
        """
        Initialize the check with the given features.

        :param features: Enabled feature flags controlling the restrictions.
        """

        self._features = features

    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        """
        Validate access to a file source.

        :param access_sources: Information about the source that is accessed.
        :return: :py:data:`~erbsland.conf.access_check.AccessCheckResult.GRANTED` if access is allowed,
            otherwise :py:data:`~erbsland.conf.access_check.AccessCheckResult.DENIED`.
        :raises ConfAccessError: If access is denied due to a restriction.
        :raises Error: If resolving a path fails.
        """

        if not isinstance(access_sources.source, SourceIdentifier):
            return AccessCheckResult.DENIED
        # Allow access to the root source.
        if access_sources.source == access_sources.root or access_sources.parent is None:
            return AccessCheckResult.GRANTED
        if access_sources.source.name != SourceIdentifier.FILE:
            # If only file sources are allowed, reject non-file sources. Otherwise, allow them.
            if self._features & AccessFeature.ONLY_FILE_SOURCES == 0:
                return AccessCheckResult.GRANTED
            raise ConfAccessError("Only file sources are allowed", source=access_sources.source)
        parent_path = Path(access_sources.parent.path)
        try:
            parent_directory = parent_path.resolve(strict=True).parent
            if not parent_directory.is_dir():
                raise Error(
                    ErrorCategory.ACCESS,
                    "Parent document is not in a directory.",
                    path=Path(access_sources.parent.path),
                )
        except FileNotFoundError:
            raise ConfAccessError("Couldn't resolve the directory of the parent path", path=parent_path)
        src_path = Path(access_sources.source.path)
        try:
            src_path = src_path.resolve(strict=True)
        except FileNotFoundError:
            raise Error(ErrorCategory.ACCESS, "Couldn't resolve source path", path=src_path)
        if AccessFeature.LIMIT_SIZE in self._features:
            file_size = src_path.stat().st_size
            if file_size > limits.MAX_DOCUMENT_SIZE:
                raise ConfAccessError(
                    f"File size exceeds limit of {limits.MAX_DOCUMENT_SIZE} bytes. size={file_size}",
                    path=src_path,
                )
        if AccessFeature.REQUIRE_SUFFIX in self._features:
            if not src_path.name.endswith(".elcl"):
                raise ConfAccessError("File name does not end with '.elcl'", path=src_path)
        if AccessFeature.ANY_DIRECTORY in self._features:
            return AccessCheckResult.GRANTED
        if src_path.parent == parent_directory:
            if AccessFeature.SAME_DIRECTORY not in self._features:
                raise ConfAccessError(
                    "Included file in the same directory as the parent is not allowed.",
                    path=src_path,
                )
            return AccessCheckResult.GRANTED
        if AccessFeature.SUBDIRECTORIES not in self._features:
            raise ConfAccessError(
                "Included file in a subdirectory is not allowed.",
            )
        if not src_path.is_relative_to(parent_directory):
            raise ConfAccessError("Included file is not in a subdirectory of the parent", path=src_path)
        return AccessCheckResult.GRANTED
