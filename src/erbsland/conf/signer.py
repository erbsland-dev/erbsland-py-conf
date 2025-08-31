#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from io import TextIOBase, RawIOBase
from pathlib import Path

from erbsland.conf.error import (
    ConfIoError,
    ConfLimitExceeded,
    ConfSignatureError,
)
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.limits import MAX_DOCUMENT_SIZE, MAX_LINE_LENGTH
from erbsland.conf.impl.text_escape import escape_text
from erbsland.conf.signature import SignatureHandler, SignatureSigningData
from erbsland.conf.source import SourceIdentifier


class Signer:
    """A tool for signing configuration documents."""

    def __init__(self, handler: SignatureHandler):
        """Initialize the signer with the given signature handler."""
        self._handler = handler

    def sign_document(self, src: Path, dst: Path, *, signing_person: str) -> None:
        """
        Sign a configuration document using *handler* and write the signed version to *dst*.

        The signing process calculates a digest of the document, asks *handler* to create a signature and finally
        writes the signed document. The source document is read a second time, and the digest is verified again before
        the real signature is written, protecting against concurrent modifications.

        :param src: The source file to sign.
        :param dst: The destination file for the signed document.
        :param signing_person: Identifier for the person performing the signing.
        :raises ConfIoError: If the source or destination cannot be accessed.
        :raises ConfLimitExceeded: If the document or the signature text exceeds size limits.
        :raises ConfEncodingError: If the document is not valid UTF-8.
        :raises ConfSignatureError: If the source file changes during signing.
        """

        source_path = self._validate_source_path(src)
        digest_text, has_windows = self._build_digest(source_path)
        source_id = SourceIdentifier(SourceIdentifier.FILE, source_path.as_posix())
        data = SignatureSigningData(source=source_id, signing_person=signing_person, document_digest=digest_text)
        signature_raw = self._handler.sign(data)
        signature_text = self._validate_and_escape_signature_text(signature_raw)
        self._write_signed_file(source_path, dst, signature_text, digest_text, has_windows)

    @staticmethod
    def _validate_source_path(path: Path) -> Path:
        """Return the canonical path of *path* and validate basic constraints."""

        try:
            resolved = path.resolve()
            if not resolved.is_file():
                raise ConfIoError("The source path is no existing regular file.", path=resolved)
            if resolved.stat().st_size > MAX_DOCUMENT_SIZE:
                raise ConfLimitExceeded("The source file is too large.", path=resolved)
            return resolved
        except (OSError, ConfIoError, ConfLimitExceeded):
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ConfIoError(
                "Could not validate the source file location or size.",
                path=path,
                system_message=str(exc),
            ) from exc

    @staticmethod
    def _is_signature_line(line: str) -> bool:
        """Return ``True`` if *line* starts with ``@signature`` (case-insensitive)."""

        bom = "\xef\xbb\xbf"
        if line.startswith(bom):
            line = line[len(bom) :]
        return line.lower().startswith("@signature")

    def _build_digest(self, path: Path) -> tuple[str, bool]:
        """Calculate the digest of *path* and detect Windows line endings."""

        has_windows = False
        source = FileSource(path)
        source.open()
        source.start_digest_calculation()
        first_line = source.readline()
        is_signature = self._is_signature_line(first_line)
        if is_signature:
            source.start_digest_calculation()  # Restart the calculation if there is a signature line.
        if "\r\n" in first_line:
            has_windows = True

        while line := source.readline():
            if not has_windows and "\r\n" in line:
                has_windows = True
        digest_text = source.get_digest()
        source.close()
        return digest_text, has_windows

    @staticmethod
    def _validate_and_escape_signature_text(text: str) -> str:
        """Validate and escape the signature text returned by the handler."""

        if not text:
            raise ConfSignatureError("The signature text is empty.")
        escaped = escape_text(text)
        if len(escaped) > MAX_LINE_LENGTH - 20:
            raise ConfLimitExceeded("The signature text is too long.")
        return escaped

    @staticmethod
    def _write_placeholder_signature(stream: RawIOBase, signature_text: str, has_windows: bool) -> None:
        placeholder = '@signature: "' + ("?" * len(signature_text)) + '"'
        placeholder += "\r\n" if has_windows else "\n"
        stream.write(placeholder.encode("utf-8"))

    def _write_configuration(self, stream: RawIOBase, source_path: Path) -> str:
        source = FileSource(source_path)
        source.open()
        source.start_digest_calculation()
        first_line = source.readline()
        is_signature = self._is_signature_line(first_line)
        if is_signature:
            # Restart the calculation if there is a signature line and ignore the first line.
            source.start_digest_calculation()
        else:
            stream.write(first_line.encode("utf-8"))
        while line := source.readline():
            stream.write(line.encode("utf-8"))
        digest_text = source.get_digest()
        source.close()
        return digest_text

    @staticmethod
    def _write_real_signature(stream: RawIOBase, signature_text: str, has_windows: bool) -> None:
        line = f'@signature: "{signature_text}"'
        line += "\r\n" if has_windows else "\n"
        stream.write(line.encode("utf-8"))

    def _write_signed_file(
        self,
        source_path: Path,
        destination_path: Path,
        signature_text: str,
        digest_text: str,
        has_windows_line_breaks: bool,
    ) -> None:
        try:
            with destination_path.open("wb+") as out_file:
                self._write_placeholder_signature(out_file, signature_text, has_windows_line_breaks)
                digest_after = self._write_configuration(out_file, source_path)
                if digest_after != digest_text:
                    raise ConfSignatureError("The source file has been modified while writing the signed version.")
                out_file.seek(0)
                self._write_real_signature(out_file, signature_text, has_windows_line_breaks)
        except ConfSignatureError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ConfIoError(
                "Could not write the signed file.", path=destination_path, system_message=str(exc)
            ) from exc
