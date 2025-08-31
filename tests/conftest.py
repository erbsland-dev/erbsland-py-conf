#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))


def _ids_factory(root: Path):
    def _id(p: Path):
        try:
            return str(p.relative_to(root).as_posix())
        except Exception:
            return str(p)

    return _id


def pytest_generate_tests(metafunc):
    if "test_case_path" not in metafunc.fixturenames:
        return

    project_root = Path(__file__).parent
    root = project_root / "erbsland-lang-config-tests" / "tests" / "V1_0"
    paths = sorted(root.rglob("*.elcl"))

    metafunc.parametrize("test_case_path", paths, ids=_ids_factory(root))
