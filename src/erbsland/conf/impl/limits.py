#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


"""
Limits enforced by the configuration parser.

Most of these limits come from the *Erbsland Configuration Language* specification.
"""


MAX_DOCUMENT_SIZE: int = 100_000_000  # 100MB
"""Maximum allowed size of a configuration document in bytes."""

MAX_LINE_LENGTH: int = 4000
"""Maximum allowed length of a line in bytes."""

MAX_NAME_LENGTH: int = 100
"""Maximum allowed length of a regular name in characters."""

MAX_TEXT_LENGTH: int = 10_000_000
"""Maximum allowed length of embedded text, code, or bytes."""

MAX_DECIMAL_DIGITS: int = 19
"""Maximum number of decimal digits."""

MAX_HEXADECIMAL_DIGITS: int = 16
"""Maximum number of hexadecimal digits."""

MAX_BINARY_DIGITS: int = 64
"""Maximum number of binary digits."""

MAX_NAME_PATH_LENGTH: int = 10
"""Maximum number of elements in a name path."""

MAX_DOCUMENT_NESTING: int = 5
"""Maximum allowed depth of nested documents."""

MAX_INCLUDE_SOURCES: int = 100
"""Maximum number of sources accepted as the result of an include directive."""
