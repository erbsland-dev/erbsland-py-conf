#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from pathlib import Path

from erbsland.conf.signature import SignatureHandler
from erbsland.conf.access_check import AccessCheck
from erbsland.conf.document import Document
from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.parser_impl import ParserImpl
from erbsland.conf.impl.parser_settings import ParserSettings
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.source import Source
from erbsland.conf.source_resolver import SourceResolver


class Parser:
    """Parse configuration data into :class:`Document` objects."""

    def __init__(self) -> None:
        """Initialize a new parser instance."""

        self._settings = ParserSettings()

    @property
    def resolver(self) -> SourceResolver:
        """Get or set the current source resolver. If set to ``None``, including files is disabled."""
        return self._settings.source_resolver

    @resolver.setter
    def resolver(self, resolver: SourceResolver) -> None:
        if resolver is not None and not isinstance(resolver, SourceResolver):
            raise ValueError("'resolver' must be a SourceResolver object")
        self._settings.source_resolver = resolver

    @property
    def access_check(self) -> AccessCheck:
        """Get or set the current access check handler."""
        return self._settings.access_check

    @access_check.setter
    def access_check(self, access_check: AccessCheck) -> None:
        if access_check is None:
            raise ValueError("'access_check' must not be None")
        if not isinstance(access_check, AccessCheck):
            raise ValueError("'access_check' must be an AccessCheck object")
        self._settings.access_check = access_check

    @property
    def signature_handler(self) -> SignatureHandler:
        """Get or set the current signature handler."""
        return self._settings.signature_handler

    @signature_handler.setter
    def signature_handler(self, signature_handler: SignatureHandler) -> None:
        if signature_handler is not None and not isinstance(signature_handler, SignatureHandler):
            raise ValueError("'signature_handler' must be a SignatureHandler object")
        self._settings.signature_handler = signature_handler

    def parse(self, source: Source | Path | str) -> Document:
        """
        Parse *source* into a :class:`erbsland.conf.Document`.

        :param source: The source to parse. This can be either a path as a string or :class:`pathlib.Path`
            instance, or an instance of :class:`Source<erbsland.conf.Source>`.
        :returns: A :class:`Document<erbsland.conf.Document>` instance with the parsed configuration.
        :raises Error: On any error while reading and parsing the given source.
        """

        if isinstance(source, Path):
            source = FileSource(source)
        elif isinstance(source, str):
            source = TextSource(source)
        elif not isinstance(source, Source):
            raise ValueError("source must be a Source, Path, or str")

        impl = ParserImpl(source, self._settings)
        return impl.parse()


def load(path: str | Path | Source) -> Document:
    """
    Parse configuration data from a file or an existing :class:`Source`.

    This call uses the default source resolver and access check implementations.
    Use an instance of :class:`Parser<erbsland.conf.Parser>` to customize these implementations.

    :param path: The source to parse. This can be either a path as a string or :class:`pathlib.Path`
        instance, or an instance of :class:`Source<erbsland.conf.Source>`.
    :returns: A :class:`Document<erbsland.conf.Document>` instance with the parsed configuration.
    :raises Error: On any error while reading and parsing the given source.
    """

    if isinstance(path, str):
        path = Path(path)
    if isinstance(path, Path):
        source = FileSource(path)
    elif isinstance(path, Source):
        source = path
    else:
        raise ValueError("Invalid 'path' type. Expected str, Path or Source")

    parser = Parser()
    return parser.parse(source)


def loads(text: str) -> Document:
    """
    Parse configuration data from a string.

    This call uses the default source resolver and access check implementations.
    Use an instance of :class:`Parser<erbsland.conf.Parser>` to customize these implementations.

    :param text: Text containing configuration data.
    :returns: A :class:`Document<erbsland.conf.Document>` instance with the parsed configuration.
    :raises Error: On any error while reading and parsing the given source.
    """

    if not isinstance(text, str):
        raise ValueError("Invalid 'text' type. Expected 'str'")
    parser = Parser()
    return parser.parse(TextSource(text))
