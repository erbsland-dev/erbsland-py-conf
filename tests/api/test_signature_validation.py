from __future__ import annotations

import re
from pathlib import Path

import codecs
import pytest

from erbsland.conf.error import ConfSignatureError
from erbsland.conf.parser import Parser
from erbsland.conf.signature import (
    SignatureHandler,
    SignatureSigningData,
    SignatureValidatorData,
    SignatureValidatorResult,
)
from erbsland.conf.signer import Signer


class _RoundTripHandler(SignatureHandler):
    def __init__(self) -> None:
        self.validate_calls: list[SignatureValidatorData] = []

    def sign(self, data: SignatureSigningData) -> str:  # type: ignore[override]
        return f"sig:{data.signing_person}:{data.document_digest}"

    def validate(self, data: SignatureValidatorData) -> SignatureValidatorResult:
        self.validate_calls.append(data)
        if not data.signature_text:
            return SignatureValidatorResult.ACCEPT
        match = re.fullmatch(r"sig:[^:]+:(?P<digest>.+)", data.signature_text)
        if match and match.group("digest") == data.document_digest:
            return SignatureValidatorResult.ACCEPT
        return SignatureValidatorResult.REJECT


@pytest.mark.parametrize(
    "content",
    [
        pytest.param('# Configuration\n[main]\nname: "value"\n', id="lf"),
        pytest.param('# Configuration\r\n[main]\r\nname: "value"\r\n', id="crlf"),
    ],
)
def test_round_trip_sign_and_validate(tmp_path: Path, content: str) -> None:
    src = tmp_path / "doc.elcl"
    signed = tmp_path / "signed.elcl"
    src.write_bytes(content.encode("utf-8"))

    handler = _RoundTripHandler()
    signer = Signer(handler)
    signer.sign_document(src, signed, signing_person="Alice")

    parser = Parser()
    parser.signature_handler = handler
    parser.parse(signed)

    assert handler.validate_calls
    assert handler.validate_calls[0].signature_text == f"sig:Alice:{handler.validate_calls[0].document_digest}"


@pytest.mark.parametrize(
    "line_break",
    [
        pytest.param("\n", id="lf"),
        pytest.param("\r\n", id="crlf"),
    ],
)
def test_round_trip_sign_and_validate_with_bom(tmp_path: Path, line_break: str) -> None:
    content = f'# Configuration{line_break}[main]{line_break}name: "value"{line_break}'
    src = tmp_path / "doc.elcl"
    signed = tmp_path / "signed.elcl"
    src.write_bytes(content.encode("utf-8"))

    handler = _RoundTripHandler()
    signer = Signer(handler)
    signer.sign_document(src, signed, signing_person="Alice")

    signed.write_bytes(codecs.BOM_UTF8 + signed.read_bytes())

    parser = Parser()
    parser.signature_handler = handler
    parser.parse(signed)

    assert handler.validate_calls
    assert handler.validate_calls[0].signature_text == f"sig:Alice:{handler.validate_calls[0].document_digest}"

def test_validation_detects_modified_document(tmp_path: Path) -> None:
    src = tmp_path / "doc.elcl"
    signed = tmp_path / "signed.elcl"
    content = '# Configuration\n[main]\nname: "value"\n'
    src.write_text(content, encoding="utf-8")

    handler = _RoundTripHandler()
    signer = Signer(handler)
    signer.sign_document(src, signed, signing_person="Alice")

    with signed.open("a", encoding="utf-8") as fh:
        fh.write('tampered: "x"\n')

    parser = Parser()
    parser.signature_handler = handler
    with pytest.raises(ConfSignatureError):
        parser.parse(signed)


def test_validation_detects_modified_signature(tmp_path: Path) -> None:
    src = tmp_path / "doc.elcl"
    signed = tmp_path / "signed.elcl"
    content = '# Configuration\n[main]\nname: "value"\n'
    src.write_text(content, encoding="utf-8")

    handler = _RoundTripHandler()
    signer = Signer(handler)
    signer.sign_document(src, signed, signing_person="Alice")

    lines = signed.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[0] = '@signature: "tampered"\n'
    signed.write_text("".join(lines), encoding="utf-8")

    parser = Parser()
    parser.signature_handler = handler
    with pytest.raises(ConfSignatureError):
        parser.parse(signed)


def test_handler_called_for_unsigned_document(tmp_path: Path) -> None:
    handler = _RoundTripHandler()
    parser = Parser()
    parser.signature_handler = handler
    parser.parse('# Configuration\n[main]\nname: "value"\n')

    assert len(handler.validate_calls) == 1
    assert handler.validate_calls[0].signature_text == ""
