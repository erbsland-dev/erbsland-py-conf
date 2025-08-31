#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from erbsland.conf.error import ConfSignatureError
from erbsland.conf.signature import SignatureHandler, SignatureValidatorData, SignatureValidatorResult
from erbsland.conf.signer import Signer
from erbsland.conf.impl.text_escape import escape_text


class _DummyHandler(SignatureHandler):
    def __init__(self) -> None:
        self.received_digest: str | None = None

    def validate(self, data: SignatureValidatorData) -> SignatureValidatorResult:  # pragma: no cover - unused
        return SignatureValidatorResult.ACCEPT

    def sign(self, data):  # type: ignore[override]
        self.received_digest = data.document_digest
        return f"sig:{data.signing_person}:{data.document_digest}"


class _TamperHandler(SignatureHandler):
    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def validate(self, data: SignatureValidatorData) -> SignatureValidatorResult:  # pragma: no cover - unused
        return SignatureValidatorResult.ACCEPT

    def sign(self, data):  # type: ignore[override]
        with self._source_path.open("a", encoding="utf-8") as fh:
            fh.write('tamper: "x"\n')
        return "tampered"


RE_SIGNATURE_LINE = re.compile(r'\A@signature: ".*?"\r?\n')


def _expected_digest(content: str) -> str:
    h = hashlib.sha3_256()
    if RE_SIGNATURE_LINE.match(content):
        content = content[RE_SIGNATURE_LINE.match(content).end() :]
    h.update(content.encode("utf-8"))
    return f"{h.name.lower()} {h.hexdigest()}"


@pytest.mark.parametrize(
    "content,expected_first_line",
    [
        pytest.param('# Configuration\n[main]\nname: "value"\n', f'@signature: "%(sig)s"\n', id="lf"),
        pytest.param('# Configuration\r\n[main]\r\nname: "value"\r\n', f'@signature: "%(sig)s"\r\n', id="crlf"),
        pytest.param(
            '@signature: "existing"\n# Configuration\n[main]\nname: "value"\n', f'@signature: "%(sig)s"\n', id="sig+lf"
        ),
        pytest.param(
            '@signature: "existing"\r\n# Configuration\r\n[main]\r\nname: "value"\r\n',
            f'@signature: "%(sig)s"\r\n',
            id="sig+crlf",
        ),
    ],
)
def test_sign_document_writes_signature(tmp_path: Path, content: str, expected_first_line: str) -> None:
    src = tmp_path / "doc.elcl"
    dst = tmp_path / "signed.elcl"
    src.write_bytes(content.encode("utf-8"))

    handler = _DummyHandler()

    signer = Signer(handler)
    signer.sign_document(src, dst, signing_person="Alice")

    expected_sig = f"sig:Alice:{_expected_digest(content)}"
    expected_first_line = expected_first_line % {"sig": escape_text(expected_sig)}

    expected_content = RE_SIGNATURE_LINE.sub("", content)

    result = dst.read_bytes().decode("utf-8")
    assert result.startswith(expected_first_line)
    assert result[len(expected_first_line) :] == expected_content
    assert handler.received_digest == _expected_digest(content)


def test_sign_document_detects_modification(tmp_path: Path) -> None:
    src = tmp_path / "doc.elcl"
    dst = tmp_path / "signed.elcl"
    content = '# Configuration\n[main]\nname: "value"\n'
    src.write_text(content, encoding="utf-8")

    handler = _TamperHandler(src)
    signer = Signer(handler)

    with pytest.raises(ConfSignatureError):
        signer.sign_document(src, dst, signing_person="Bob")
