# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Literal behavioral fixtures adapted from Erbsland Core's Apache-2.0 VR tests."""

import json
from pathlib import Path

import pytest

from erbsland.conf import ConfValidationError, loads
from erbsland.conf.vr import Rules

CASES = json.loads((Path(__file__).parent / "data" / "core_cases.json").read_text())
CASES += json.loads((Path(__file__).parent / "data" / "core_matrix.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_core_behavior(case):
    if "document" not in case:
        # Syntax errors belong to the ELCL parser; these are valid ELCL schemas.
        document = loads(case["rules"])
        if case["valid"]:
            Rules.from_document(document)
        else:
            with pytest.raises(ConfValidationError):
                Rules.from_document(document)
    else:
        rules = Rules.loads(case["rules"])
        document = loads(case["document"])
        if case["valid"]:
            rules.validate(document, case["version"])
        else:
            with pytest.raises(ConfValidationError):
                rules.validate(document, case["version"])
