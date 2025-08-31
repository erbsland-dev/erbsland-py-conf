#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from dataclasses import dataclass, field

from erbsland.conf.signature import SignatureHandler
from erbsland.conf.access_check import AccessCheck
from erbsland.conf.file_access_check import FileAccessCheck
from erbsland.conf.file_source_resolver import FileSourceResolver
from erbsland.conf.source_resolver import SourceResolver


@dataclass(slots=True)
class ParserSettings:
    """
    Configuration options used during parsing.

    :var source_resolver: Component used to resolve referenced sources.
    :var access_check: Access-check implementation that validates file access.
    :var signature_handler: Signature validator implementation that validates the signature of the configuration.
    """

    source_resolver: SourceResolver | None = field(default_factory=FileSourceResolver)
    access_check: AccessCheck | None = field(default_factory=FileAccessCheck)
    signature_handler: SignatureHandler | None = None
