#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


SUPPORTED_FEATURES: set[str] = {
    "core",
    "minimum",
    "standard",
    "advanced",
    "all",
    "float",
    "byte-count",
    "multi-line",
    "section-list",
    "value-list",
    "text-names",
    "date-time",
    "code",
    "byte-data",
    "include",
    "regex",
    "time-delta",
    "validation",
    "signature",
}
"""Set of all feature names supported by the parser."""
