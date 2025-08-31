#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from typing import Generator

from erbsland.conf.impl.token import Token


TokenGenerator = Generator[Token, None, None]
"""Generator yielding tokens produced by the lexing methods."""

TokenList = list[Token]
"""List of tokens returned by the scanning methods."""
