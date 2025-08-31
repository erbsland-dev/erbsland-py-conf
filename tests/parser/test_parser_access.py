#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from erbsland.conf.parser import Parser
from erbsland.conf.file_access_check import FileAccessCheck, AccessFeature, ConfAccessError


class IncludeFile(Enum):
    SAME_DIRECTORY = auto()
    SUBDIRECTORY = auto()
    PARENT_DIRECTORY = auto()
    WRONG_SUFFIX = auto()


@dataclass(frozen=True, slots=True)
class IncludeFileData:
    path: Path
    include_text: str


FILE_DATA: dict[IncludeFile, IncludeFileData] = {
    IncludeFile.SAME_DIRECTORY: IncludeFileData(Path("config/file.elcl"), "file.elcl"),
    IncludeFile.SUBDIRECTORY: IncludeFileData(Path("config/sub/file.elcl"), "sub/file.elcl"),
    IncludeFile.PARENT_DIRECTORY: IncludeFileData(Path("file.elcl"), "../file.elcl"),
    IncludeFile.WRONG_SUFFIX: IncludeFileData(Path("config/file.txt"), "file.txt"),
}


@dataclass(frozen=True, slots=True)
class AccessCase:
    include_file: IncludeFile
    enabled: tuple[AccessFeature, ...]
    disabled: tuple[AccessFeature, ...]
    expect_success: bool


def _make_test_cases() -> list:
    cases: list = []
    raw_cases = [
        AccessCase(IncludeFile.PARENT_DIRECTORY, (), (), False),
        AccessCase(IncludeFile.SAME_DIRECTORY, (), (), True),
        AccessCase(IncludeFile.SUBDIRECTORY, (), (), True),
        AccessCase(IncludeFile.WRONG_SUFFIX, (), (), True),
        # disable SAME_DIRECTORY
        AccessCase(IncludeFile.PARENT_DIRECTORY, (), (AccessFeature.SAME_DIRECTORY,), False),
        AccessCase(IncludeFile.SAME_DIRECTORY, (), (AccessFeature.SAME_DIRECTORY,), False),
        AccessCase(IncludeFile.SUBDIRECTORY, (), (AccessFeature.SAME_DIRECTORY,), True),
        AccessCase(IncludeFile.WRONG_SUFFIX, (), (AccessFeature.SAME_DIRECTORY,), False),
        # disable SUBDIRECTORIES
        AccessCase(IncludeFile.PARENT_DIRECTORY, (), (AccessFeature.SUBDIRECTORIES,), False),
        AccessCase(IncludeFile.SAME_DIRECTORY, (), (AccessFeature.SUBDIRECTORIES,), True),
        AccessCase(IncludeFile.SUBDIRECTORY, (), (AccessFeature.SUBDIRECTORIES,), False),
        AccessCase(IncludeFile.WRONG_SUFFIX, (), (AccessFeature.SUBDIRECTORIES,), True),
        # disable SAME_DIRECTORY and SUBDIRECTORIES
        AccessCase(
            IncludeFile.PARENT_DIRECTORY,
            (),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            False,
        ),
        AccessCase(
            IncludeFile.SAME_DIRECTORY,
            (),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            False,
        ),
        AccessCase(
            IncludeFile.SUBDIRECTORY,
            (),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            False,
        ),
        AccessCase(
            IncludeFile.WRONG_SUFFIX,
            (),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            False,
        ),
        # enable ANY_DIRECTORY
        AccessCase(IncludeFile.PARENT_DIRECTORY, (AccessFeature.ANY_DIRECTORY,), (), True),
        AccessCase(IncludeFile.SAME_DIRECTORY, (AccessFeature.ANY_DIRECTORY,), (), True),
        AccessCase(IncludeFile.SUBDIRECTORY, (AccessFeature.ANY_DIRECTORY,), (), True),
        AccessCase(IncludeFile.WRONG_SUFFIX, (AccessFeature.ANY_DIRECTORY,), (), True),
        # enable ANY_DIRECTORY and disable SAME_DIRECTORY and SUBDIRECTORIES
        AccessCase(
            IncludeFile.PARENT_DIRECTORY,
            (AccessFeature.ANY_DIRECTORY,),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            True,
        ),
        AccessCase(
            IncludeFile.SAME_DIRECTORY,
            (AccessFeature.ANY_DIRECTORY,),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            True,
        ),
        AccessCase(
            IncludeFile.SUBDIRECTORY,
            (AccessFeature.ANY_DIRECTORY,),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            True,
        ),
        AccessCase(
            IncludeFile.WRONG_SUFFIX,
            (AccessFeature.ANY_DIRECTORY,),
            (AccessFeature.SAME_DIRECTORY, AccessFeature.SUBDIRECTORIES),
            True,
        ),
        # enable REQUIRE_SUFFIX
        AccessCase(IncludeFile.PARENT_DIRECTORY, (AccessFeature.REQUIRE_SUFFIX,), (), False),
        AccessCase(IncludeFile.SAME_DIRECTORY, (AccessFeature.REQUIRE_SUFFIX,), (), True),
        AccessCase(IncludeFile.SUBDIRECTORY, (AccessFeature.REQUIRE_SUFFIX,), (), True),
        AccessCase(IncludeFile.WRONG_SUFFIX, (AccessFeature.REQUIRE_SUFFIX,), (), False),
    ]
    for index, case in enumerate(raw_cases):
        cases.append(pytest.param(case, id=f"{index}-{case.include_file.name}"))
    return cases


@pytest.mark.parametrize("case", _make_test_cases())
def test_access_check_for_includes(tmp_path, case: AccessCase):
    file_data = FILE_DATA[case.include_file]
    main_path = tmp_path / "config" / "main.elcl"
    main_path.parent.mkdir(parents=True, exist_ok=True)
    include_path = tmp_path / file_data.path
    include_path.parent.mkdir(parents=True, exist_ok=True)
    main_content = f'[main]\nvalue: 123\n@include: "{file_data.include_text}"\n'
    main_path.write_text(main_content, encoding="utf-8")
    include_path.write_text("[other]\nvalue: 456\n", encoding="utf-8")
    features = AccessFeature.DEFAULTS
    for feature in case.enabled:
        features |= feature
    for feature in case.disabled:
        features &= ~feature
    parser = Parser()
    parser.access_check = FileAccessCheck(features)
    if case.expect_success:
        parser.parse(main_path)
    else:
        with pytest.raises(ConfAccessError):
            parser.parse(main_path)
