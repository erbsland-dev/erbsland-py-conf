#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import enum


class TestOutput(enum.IntFlag):
    """Format flags for displaying test output."""

    CONTAINER_SIZE = enum.auto()
    """Display the container size."""
    POSITION = enum.auto()
    """Display the position in the document."""
    SOURCE_ID = enum.auto()
    """Display the source identifier."""
    MINIMAL_ESC = enum.auto()
    """Only escape special characters."""
    ALIGN_VALUES = enum.auto()
    """Align the arrows and values in value tree output."""

    DEFAULT = 0
    """Default format."""
