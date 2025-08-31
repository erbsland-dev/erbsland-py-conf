#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from typing import Final


class MissingType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "MISSING"  # pragma: no cover


MISSING: Final = MissingType()
