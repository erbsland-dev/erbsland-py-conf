#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from erbsland.conf.access_check import AccessSources, AccessCheckResult
from erbsland.conf.document import Document
from erbsland.conf.error import ConfSyntaxError, ConfAccessError
from erbsland.conf.error import (
    Error,
    ConfInternalError,
    ConfSignatureError,
    ConfUnsupportedError,
)
from erbsland.conf.impl.assignment import Assignment, AssignmentStream, AssignmentGenerator, AssignmentType
from erbsland.conf.impl.document_impl import DocumentBuilderImpl
from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.limits import MAX_INCLUDE_SOURCES, MAX_DOCUMENT_NESTING
from erbsland.conf.impl.parser_settings import ParserSettings
from erbsland.conf.location import Location, Position
from erbsland.conf.name import META_NAME_INCLUDE, META_NAME_SIGNATURE, Name
from erbsland.conf.signature import SignatureValidatorData, SignatureValidatorResult
from erbsland.conf.source import Source, SourceIdentifier
from erbsland.conf.source_resolver import SourceResolverContext


class ParserContext:
    """Holds the parsing state for a single source, including nested includes."""

    def __init__(self, include_level: int, source: Source, settings: ParserSettings):
        """Initialize the context for the given source and parser settings."""

        self._include_level: int = include_level
        assert source is not None
        self._source = source
        self._settings = settings
        self._assignment_stream: AssignmentStream | None = None
        self._lexer: Lexer | None = None
        self._initialized = False
        self._assignment_generator: AssignmentGenerator | None = None
        self._is_at_end = False
        self._signature_text: str = ""

    @property
    def initialized(self) -> bool:
        """Return ``True`` if the context has been initialized."""

        return self._initialized

    def initialize(self) -> None:
        """Open the source and prepare the lexer and assignment stream."""

        assert not self._initialized
        assert self._source is not None
        self._source.open()
        digest_enabled = self._settings.signature_handler is not None
        self._lexer = Lexer(self._source, digest_enabled=digest_enabled)
        self._assignment_stream = AssignmentStream(self._lexer, self._source.identifier)
        self._assignment_generator = self._assignment_stream.assignments()
        self._initialized = True

    def has_next(self) -> bool:
        """Return ``True`` if more assignments are available."""

        assert self._initialized
        assert self._assignment_generator is not None
        return not self._is_at_end

    def next_assignment(self) -> Assignment:
        """Return the next assignment and update the end-of-document state."""

        assert self._initialized
        assert self._assignment_generator is not None
        assignment = next(self._assignment_generator)
        if assignment is None or assignment.type == AssignmentType.END_OF_DOCUMENT:
            self._is_at_end = True
        return assignment

    # --- properties -----------------------------------------------------

    @property
    def include_level(self) -> int:
        """Nesting depth of the current document."""

        return self._include_level

    @property
    def source_identifier(self) -> SourceIdentifier:
        """Identifier of the source associated with this context."""

        assert self._source is not None
        return self._source.identifier

    @property
    def signature_text(self) -> str:
        """Collected signature text for this document."""

        return self._signature_text

    @signature_text.setter
    def signature_text(self, text: str) -> None:
        self._signature_text = text

    def get_digest(self) -> str:
        """Return the digest of the source associated with this context."""
        return self._source.get_digest()

    def close(self) -> None:
        """Release resources associated with this context."""

        # Allow early release of resources
        self._source.close()
        self._source = None
        self._lexer = None
        self._assignment_stream = None
        self._assignment_generator = None


class ParserImpl:
    """Internal parser used by :class:`erbsland.conf.parser.Parser`."""

    def __init__(self, source: Source, settings: ParserSettings):
        """Create a parser for the given source and settings."""

        if source is None:
            raise ValueError("Source must not be None")  # pragma: no cover
        if settings is None:
            raise ValueError("Settings must not be None")  # pragma: no cover
        if not isinstance(source, Source):
            raise ValueError("'source' must be a Source object")  # pragma: no cover
        if not isinstance(settings, ParserSettings):
            raise ValueError("'settings' must be a ParserSettings object")  # pragma: no cover
        self._source = source
        self._settings = settings
        # Prepare a stack with the root context
        self._context_stack: list[ParserContext] = []
        # The root document starts at line 1, column 1 in the first source.
        source_location = Location(self._source.identifier, Position(1, 1))
        self._builder = DocumentBuilderImpl(document_location=source_location)
        self._add_included_source(self._source, location=source_location)

    # --- parsing -----------------------------------------------------

    def _root_context(self) -> ParserContext:
        """Return the root parser context."""
        if not self._context_stack:
            raise ConfInternalError("No parser context available")  # pragma: no cover
        return self._context_stack[0]

    def _current_context(self) -> ParserContext:
        """Return the current parser context."""

        if not self._context_stack:
            raise ConfInternalError("No parser context available")  # pragma: no cover
        return self._context_stack[-1]

    def parse(self) -> Document:
        """Parse the source and return a :class:`Document`."""

        try:
            while self._context_stack:
                context = self._current_context()
                if not context.initialized:
                    context.initialize()
                if context.has_next():
                    assignment = context.next_assignment()
                    self._process_assignment(assignment)
                else:
                    self._pre_leave_processing(context)
                    context.close()
                    self._context_stack.pop()
            return self._builder.get_document_and_reset()
        except Error as error:
            # Ensure all contexts are closed on error
            for ctx in self._context_stack:
                try:
                    ctx.close()
                except Error:
                    pass
            # If the error is related to a named assignment, add the last section as context.
            if error.name_path and self._builder.last_section:
                raise error.with_name_path(self._builder.last_section.name_path / error.name_path) from error
            raise

    # --- assignment processing --------------------------------------

    def _process_assignment(self, assignment: Assignment) -> None:
        """Process a single assignment produced by the lexer."""

        match assignment.type:
            case AssignmentType.END_OF_DOCUMENT:
                return
            case AssignmentType.SECTION_MAP:
                assert assignment.name_path is not None
                self._builder.add_section_map(assignment.name_path, assignment.location)
            case AssignmentType.SECTION_LIST:
                assert assignment.name_path is not None
                self._builder.add_section_list(assignment.name_path, assignment.location)
            case AssignmentType.VALUE:
                assert assignment.name_path is not None
                assert assignment.value is not None
                self._builder.add_value(assignment.name_path, assignment.value, assignment.location)
            case AssignmentType.META_VALUE:
                assert assignment.name_path is not None
                assert assignment.value is not None
                self._process_meta_value(assignment)
            case _:  # pragma: no cover
                assert False, "Unsupported assignment type"  # pragma: no cover

    def _process_meta_value(self, assignment: Assignment) -> None:
        """Handle meta-value assignments."""

        assert assignment.name_path is not None and assignment.value is not None
        name: Name = list(assignment.name_path)[-1]
        if name == META_NAME_SIGNATURE:
            self._current_context().signature_text = assignment.value.as_text()
        elif name == META_NAME_INCLUDE:
            if self._settings.source_resolver is None:
                raise ConfUnsupportedError("The @include meta-command is disabled", source=assignment.location)
            if self._current_context().include_level >= MAX_DOCUMENT_NESTING:
                raise ConfSyntaxError("Maximum document nesting level reached", source=assignment.location)
            resolve_context = SourceResolverContext(
                str(assignment.value.native),
                self._current_context().source_identifier,
            )
            try:
                sources = self._settings.source_resolver.resolve(resolve_context)
            except Error as e:
                raise e.with_source(assignment.location) from e
            except Exception as e:
                raise ConfInternalError(
                    f"An unexpected error occurred while resolving the include pattern: {str(e)}",
                    source=assignment.location,
                ) from e
            if not isinstance(sources, list):
                raise ConfInternalError(
                    "The source resolver did not return a list of sources.",
                    source=assignment.location,
                )
            if len(sources) > MAX_INCLUDE_SOURCES:
                raise ConfSyntaxError(
                    f"The '@include' meta-command would include too many sources ({len(sources)} > {MAX_INCLUDE_SOURCES})",
                    source=assignment.location,
                )
            root_source_id = self._root_context().source_identifier
            parent_source_id = self._current_context().source_identifier
            for source in reversed(sources):
                self._add_included_source(source, parent=parent_source_id, location=assignment.location)

        # Other meta-values are handled by the lexer/assignment stream.

    def _add_included_source(
        self,
        source: Source,
        *,
        parent: SourceIdentifier | None = None,
        location: Location | None = None,
    ) -> None:
        """Add the current source to the stack."""
        assert source is not None
        assert parent is None or isinstance(parent, SourceIdentifier)
        assert location is None or isinstance(location, Location)
        if not isinstance(source, Source):
            raise ConfInternalError(
                "The list returned by the source resolver contained non-Source objects",
                source=location,
            )
        if self._settings.access_check is None:
            raise ConfAccessError("Access check is disabled. Cannot grant access to sources")
        try:
            source_id = source.identifier
            assert source_id is not None and isinstance(source_id, SourceIdentifier)
            access_sources = AccessSources(source=source_id, parent=parent, root=self._source.identifier)
            result = self._settings.access_check.check(access_sources)
        except ConfAccessError as e:
            if location and e.location is None:
                raise e.with_source(location) from e
            raise
        except Exception as e:
            raise ConfInternalError(
                f"An unexpected error occurred while checking access to the included source: {str(e)}",
                source=location,
            ) from e
        if not isinstance(result, AccessCheckResult):
            raise ConfInternalError("Access check did not return an AccessCheckResult object")
        if result == AccessCheckResult.DENIED:
            raise ConfAccessError("Access to the included source was denied", source=location)
        next_include_level = self._current_context().include_level + 1 if self._context_stack else 0
        if next_include_level > MAX_DOCUMENT_NESTING:
            raise ConfSyntaxError("Maximum document nesting level reached", source=location)
        new_context = ParserContext(next_include_level, source, self._settings)
        self._context_stack.append(new_context)

    # --- signature validation ----------------------------------------------

    def _pre_leave_processing(self, context: ParserContext) -> None:
        """Perform final checks before leaving a parser context."""

        if self._settings.signature_handler is None:
            if context.signature_text:
                raise ConfSignatureError("Signature cannot be verified", source=context.source_identifier)
            return
        data = SignatureValidatorData(context.source_identifier, context.signature_text, context.get_digest())
        try:
            result = self._settings.signature_handler.validate(data)
            if result == SignatureValidatorResult.REJECT:
                raise ConfSignatureError("Signature validation failed", source=context.source_identifier)
        except Error as e:
            if e.location is None:
                raise e.with_source(context.source_identifier) from e
            raise
