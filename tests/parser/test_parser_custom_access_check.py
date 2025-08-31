#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.access_check import AccessCheck, AccessSources, AccessCheckResult
from erbsland.conf.error import ConfAccessError, ConfInternalError
from erbsland.conf.parser import Parser


class RecordingAccessCheck(AccessCheck):
    def __init__(self, result: AccessCheckResult) -> None:
        self._result = result
        self.calls: list[AccessSources] = []

    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        self.calls.append(access_sources)
        return self._result


class RaisingAccessCheck(AccessCheck):
    def __init__(self) -> None:
        self._calls = 0

    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        if self._calls == 0:
            self._calls += 1
            return AccessCheckResult.GRANTED
        raise ValueError("boom")


class ReturningAccessCheck(AccessCheck):
    def __init__(self, result: object) -> None:
        self._result = result
        self._calls = 0

    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        if self._calls == 0:
            self._calls += 1
            return AccessCheckResult.GRANTED
        return self._result


@pytest.mark.parametrize(
    "result, expect_success, expected_calls",
    [
        pytest.param(AccessCheckResult.GRANTED, True, 2, id="granted"),
        pytest.param(AccessCheckResult.DENIED, False, 1, id="denied"),
    ],
)
def test_parser_with_custom_access_check(
    tmp_path, result: AccessCheckResult, expect_success: bool, expected_calls: int
) -> None:
    main = tmp_path / "main.elcl"
    included = tmp_path / "other.elcl"
    main.write_text('[main]\n@include: "other.elcl"\n', encoding="utf-8")
    included.write_text("[other]\nvalue: 1\n", encoding="utf-8")

    access_check = RecordingAccessCheck(result)
    parser = Parser()
    parser.access_check = access_check

    if expect_success:
        parser.parse(main)
    else:
        with pytest.raises(ConfAccessError):
            parser.parse(main)

    assert len(access_check.calls) == expected_calls
    if expect_success:
        sources = access_check.calls[1]
        assert sources.source.path == included.as_posix()
        assert sources.parent is not None
        assert sources.parent.path == main.as_posix()
        assert sources.root.path == main.as_posix()


@pytest.mark.parametrize(
    "access_check, expected_message",
    [
        pytest.param(
            RaisingAccessCheck(),
            "An unexpected error occurred while checking access to the included source: boom",
            id="raises-exception",
        ),
        pytest.param(
            ReturningAccessCheck(1),
            "Access check did not return an AccessCheckResult object",
            id="return-int",
        ),
        pytest.param(
            ReturningAccessCheck("granted"),
            "Access check did not return an AccessCheckResult object",
            id="return-str",
        ),
    ],
)
def test_parser_with_faulty_access_check(tmp_path, access_check: AccessCheck, expected_message: str) -> None:
    main = tmp_path / "main.elcl"
    included = tmp_path / "other.elcl"
    main.write_text('[main]\n@include: "other.elcl"\n', encoding="utf-8")
    included.write_text("[other]\nvalue: 1\n", encoding="utf-8")

    parser = Parser()
    parser.access_check = access_check

    with pytest.raises(ConfInternalError) as excinfo:
        parser.parse(main)

    assert expected_message in str(excinfo.value)
