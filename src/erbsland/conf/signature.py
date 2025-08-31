#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

from erbsland.conf.source import SourceIdentifier


class SignatureValidatorResult(enum.Enum):
    """The result of a signature validation."""

    ACCEPT = "Accept"
    """The signature is valid."""
    REJECT = "Reject"
    """The signature is invalid."""


@dataclass(frozen=True, slots=True)
class SignatureValidatorData:
    """Data for a signature validation."""

    source: SourceIdentifier
    """Identifier of the source that contains the signature."""
    signature_text: str
    """The raw text from the signature meta-value."""
    document_digest: str
    """The digest of the document in the format "<algorithm> <digest hex>"."""


@dataclass(frozen=True, slots=True)
class SignatureSigningData:
    """Data for signing a document."""

    source: SourceIdentifier
    """Identifier of the source for the signature."""
    signing_person: str
    """The text that identifies the signing person (e.g. name/email)."""
    document_digest: str
    """The digest of the document in the format "<algorithm> <digest hex>"."""


class SignatureHandler(ABC):
    """Interface for validating and creating signatures."""

    @abstractmethod
    def validate(self, data: SignatureValidatorData) -> SignatureValidatorResult:
        """
        Validate the signature.

        If a signature handler is enabled for a parser, this method is called for every document -
        regardless if it contains a signature or not.

        Instead of returning ``REJECT``, the handler can raise a
        :class:`~erbsland.conf.error.ConfSignatureError` exception.

        :returns: The result of the validation.
        :throws ConfSignatureError: Optionally, if the signature is invalid.
        """

    def sign(self, data: SignatureSigningData) -> str:
        """
        Create a signature for the document.

        This is called from the signing tool to create a signature for a document.

        :returns: The final text of the signature meta-value.
        """
        raise NotImplementedError()
