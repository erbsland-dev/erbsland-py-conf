#  Copyright (c) 2024-2025 Tobias Erbsland - Erbsland DEV. https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import datetime
import enum
import re
from typing import Any, Callable

from pygments.lexer import bygroups, ExtendedRegexLexer, LexerContext, include
from pygments.token import (
    Name,
    Whitespace,
    Comment,
    Operator,
    Keyword,
    Literal,
    Punctuation,
    String,
    Number,
    Token,
    Error,
)


class DocumentError(Exception):
    def __init__(self, pos: int, matched_text: str, message: str = ""):
        self.pos = pos
        self.matched_text = matched_text
        self.message = message


class InternalError(Exception):
    pass


class NameType(enum.StrEnum):
    """The type of name."""

    REGULAR = "regular"
    TEXT = "text"
    META = "meta"


class ValueType(enum.StrEnum):
    """The type of value."""

    UNDEF = "Undef"
    INTEGER = "Integer"
    BOOLEAN = "Boolean"
    FLOAT = "Float"
    TEXT = "Text"
    DATE = "Date"
    TIME = "Time"
    DATETIME = "DateTime"
    BYTES = "Bytes"
    TIME_DELTA = "TimeDelta"
    REGEX = "RegEx"
    VALUE_LIST = "ValueList"
    SECTION_LIST = "SectionList"
    INTERMEDIATE_SECTION = "IntermediateSection"  # = Section that was created to bridge a name path.
    SECTION_WITH_NAMES = "SectionWithNames"  # = Section with names as keys
    SECTION_WITH_TEXTS = "SectionWithTexts"  # = Section with text as keys
    DOCUMENT = "Document"  # = The document root.

    def is_map(self) -> bool:
        return self in [
            self.INTERMEDIATE_SECTION,
            self.SECTION_WITH_NAMES,
            self.SECTION_WITH_TEXTS,
            self.DOCUMENT,
        ]


class OpenState(enum.StrEnum):
    """Open states."""

    SECTION = "["
    NAME = "name"
    TEXT = '"'
    MULTILINE_TEXT = '"""'
    CODE = "`"
    MULTILINE_CODE = "```"
    REGEX = "/"
    MULTILINE_REGEX = "///"
    BYTE_DATA = "<"
    MULTILINE_BYTE_DATA = "<<<"


class ElclContext(LexerContext):
    """Data for the current context."""

    def __init__(self, text: str, pos: int = 0):
        super().__init__(text, pos)
        self.root = Value("", ValueType.SECTION_WITH_NAMES, None, None)  # The document root.
        self.section_type = SectionType.MAP  # The current section type
        self.section_error_message = ""  # If there is an error in the current section.
        self.section_is_relative = False  # If the current section is relative.
        self.section_name_parts: list[str] = []  # List to build the current section name.
        self.section: Value | None = None  # The current section.
        self.absolute_section: Value | None = None  # The absolute section.
        self.value: Value | None = None  # The current value.
        self.value_text: str = ""  # The current text
        self.value_data: bytes = b""  # The current data
        self.indent_pattern: str = ""  # The current indent pattern.
        self.open_states: list[OpenState] = []  # A state that must be closed

    def open_state(self, state: OpenState):
        self.open_states.append(state)

    def close_state(self):
        if not self.open_states:
            raise InternalError("Closed a state, not no state was open.")
        self.open_states.pop()


RE_TEXT_ESCAPE = re.compile(r'\\(?:[\\"$nrt]|u(?:[a-fA-F0-9]{4}|\{[a-fA-F0-9]{1,8}\}))')
TEXT_ESCAPE_SUBSTITUTIONS = {
    "\\": "\\",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "$": "$",
}


def normalize_name(name: str) -> str:
    """Normalize regular and text names."""
    if name.startswith('"'):  # is text?
        if name == '""':
            raise InternalError(f"An empty text name is not allowed.")
        name = normalize_text(name)
    else:
        name = name.lower().replace(" ", "_")
        if len(name) > 100:
            raise InternalError(f'The name "{name[:16]}..." exceeds 100 characters.')
    return name


def normalize_text(text: str) -> str:
    """Normalize text by resolving escape characters."""

    def replace(match: re.Match):
        result = match.group(0)
        match result[1]:
            case v if v in TEXT_ESCAPE_SUBSTITUTIONS:
                result = TEXT_ESCAPE_SUBSTITUTIONS[result[1]]
            case "u":
                if result[2] == "{":
                    result = chr(int(result[3:-1], 16))
                else:
                    result = chr(int(result[2:], 16))
        return result

    return RE_TEXT_ESCAPE.sub(replace, text)


class Value:
    """One single value in the data model."""

    RE_OUTCOME_ESCAPE = re.compile(r"[\\\".=\x00-\x1F\u007F-]")

    def __init__(self, name: str, value_type: ValueType, parent: Value = None, data: Any = None):
        self._name = normalize_name(name)
        self._type = value_type
        self._parent: Value | None = parent
        self._data = data
        self._children: dict[str, Value] | list[Value] | None = None
        self._path: list[str] = self._create_path()
        match value_type:
            case ValueType.VALUE_LIST | ValueType.SECTION_LIST:
                self._children = []
            case (
                ValueType.SECTION_WITH_NAMES
                | ValueType.SECTION_WITH_TEXTS
                | ValueType.INTERMEDIATE_SECTION
                | ValueType.DOCUMENT
            ):
                self._children = {}
            case _:
                self._children = None
        if parent:
            self._parent._add_value(self)

    def _create_path(self) -> list[str]:
        if self._parent:
            return self._parent._path + [self._name]
        else:
            return [self._name] if self._name else []

    @staticmethod
    def _escape_text(match: re.Match):
        c = match.group(0)
        return f"\\u{{{ord(c):x}}}"

    def __str__(self):
        match self._type:
            case ValueType.VALUE_LIST:
                text = ", ".join(str(v) for v in self._children)
            case ValueType.INTERMEDIATE_SECTION:
                text = ""
            case (
                ValueType.SECTION_WITH_NAMES
                | ValueType.DOCUMENT
                | ValueType.SECTION_WITH_TEXTS
                | ValueType.SECTION_LIST
            ):
                text = f"size={len(self._children)}"
            case ValueType.UNDEF:
                text = ""
            case ValueType.INTEGER | ValueType.FLOAT:
                text = str(self._data)
            case ValueType.BOOLEAN:
                text = "true" if self._data else "false"
            case ValueType.TEXT:
                text = '"' + self.RE_OUTCOME_ESCAPE.sub(self._escape_text, str(self._data)) + '"'
            case ValueType.BYTES:
                text = f"hex:{self._data.hex()}"
            case ValueType.DATE:
                text = self._data.strftime("%Y-%m-%d")
            case ValueType.TIME:
                text = self._data.strftime("%H:%M:%S%Z")
            case ValueType.DATETIME:
                text = self._data.strftime("%Y-%m-%dT%H:%M:%S%Z")
            case _:
                text = "Not supported"
        return f"{self._type}({text})"

    def get_name_visualization(self) -> str:
        """Get the visualization for the name in value trees."""
        if self.is_root():
            return "(root)"
        if self.is_section():
            if self.is_list():
                return f"*[{self._name}]"
            return f"[{self._name}]"
        return self._name

    def _add_value(self, new_value: Value):
        """Add a new value to this."""
        if new_value.has_text_name and self._type == ValueType.SECTION_WITH_NAMES:
            # Switch the map type if required. No validity check at this point!
            self._type = ValueType.SECTION_WITH_TEXTS
        normalized_name = normalize_name(new_value.name)
        if self._type.is_map():
            self._children[normalized_name] = new_value
        elif self._type == ValueType.VALUE_LIST or self._type == ValueType.SECTION_LIST:
            new_value._name = str(len(self._children))
            new_value._path = new_value._create_path()
            self._children.append(new_value)
        else:
            raise InternalError(f"Cannot add value to `{self._type}`.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> ValueType:
        return self._type

    @type.setter
    def type(self, value_type: ValueType):
        self._type = value_type

    @property
    def parent(self) -> "Value | None":
        return self._parent

    @property
    def data(self) -> Any:
        return self._data

    @data.setter
    def data(self, data: Any):
        self._data = data

    @property
    def path(self) -> list[str]:
        return self._path.copy()

    @property
    def children(self) -> dict[str, Value] | list[Value] | None:
        if self._children is None:
            return None
        return self._children.copy()

    def is_root(self) -> bool:
        return self._parent is None

    def is_empty(self) -> bool:
        if self.is_list() or self.is_map():
            return len(self._children) == 0
        if self._type is ValueType.TEXT:
            return bool(self._data)
        return False

    def is_list(self) -> bool:
        """Test if this is any kind of list."""
        return self._type in [ValueType.VALUE_LIST, ValueType.SECTION_LIST]

    def is_map(self) -> bool:
        """Test if this is any kind of map."""
        return self._type in [
            ValueType.SECTION_WITH_NAMES,
            ValueType.SECTION_WITH_TEXTS,
            ValueType.INTERMEDIATE_SECTION,
            ValueType.DOCUMENT,
        ]

    def is_section(self) -> bool:
        """Test if this is any kind of section."""
        return self._type in [
            ValueType.SECTION_WITH_NAMES,
            ValueType.SECTION_WITH_TEXTS,
            ValueType.INTERMEDIATE_SECTION,
            ValueType.SECTION_LIST,
            ValueType.DOCUMENT,
        ]

    def has_sections(self) -> bool:
        """Test is this is a map, and it contains subsections."""
        if not self.is_map():
            return False
        return any(value.is_section() for value in self._children.values())

    def has_values(self) -> bool:
        """Test if this is a map, and it contains values."""
        if not self.is_map():
            return False
        return any(not value.is_section() for value in self._children.values())

    def children_sorted_for_display(self) -> list[Value]:
        """Get a list of children sorted for display."""
        result = []
        if isinstance(self._children, list):
            result = self._children
        elif isinstance(self._children, dict):
            result = list(self._children.values())
        if not result:
            return []

        def sort_key(value: Value):  # Sort sections before values, then a-z
            if value.is_section():
                return f"a{value.name}"
            return f"b{value.name}"

        return list(sorted(result, key=sort_key))

    @property
    def has_text_name(self) -> bool:
        return self._name.startswith('"')

    def value_by_path(self, name_path: list[str]) -> Value | None:
        if not isinstance(name_path, list) or len(name_path) == 0:
            return None
        v = self.value(name_path[0])
        if v is None or len(name_path) == 1:
            return v
        return v.value_by_path(name_path[1:])

    def value(self, name: str) -> "Value | None":
        """
        Lookup a child value by name.
        For lists of maps, the last map in the list is checked.
        """
        if self._children is None:
            return None
        if self._type in [
            ValueType.SECTION_WITH_NAMES,
            ValueType.INTERMEDIATE_SECTION,
            ValueType.DOCUMENT,
        ]:
            return self._children.get(normalize_name(name), None)
        if self._type == ValueType.SECTION_WITH_TEXTS:
            return self._children.get(name, None)
        if self._type == ValueType.SECTION_LIST:
            if self._children:
                return self._children[-1].value(name)
        return None

    def create_missing_maps(self, name_path: list[str]) -> Value:
        """Create all missing paths in `name_path` and return the last element."""
        if not isinstance(name_path, list):
            raise ValueError("name_path is no list")
        if not name_path:
            return self
        v = self.value(name_path[0])
        if v is None:
            v = self.__class__(name_path[0], ValueType.INTERMEDIATE_SECTION, self)
        elif v.type == ValueType.SECTION_LIST:
            # If we encounter a list of sections, only the last element is relevant to us.
            v = v._children[-1]
        if len(name_path) == 1:
            return v
        return v.create_missing_maps(name_path[1:])

    def all_values(self):
        """Return all values as a flat list"""
        if self._path:
            yield self
        if isinstance(self._children, list):
            for child in self._children:
                yield from child.all_values()
        elif isinstance(self._children, dict):
            for child in self._children.values():
                yield from child.all_values()


class SectionType(enum.Enum):
    """
    The type of section.
    """

    MAP = enum.auto()  # A map of values, defined once.
    LIST = enum.auto()  # A list of maps, with multiple definitions.


def yield_error(lexer, pos, text, error_message=""):
    """
    Dummy error generator for debugging.
    """
    if lexer.error_tracing_enabled:
        raise DocumentError(pos, text, error_message)
    yield pos, Error, text


def handle_error(lexer, match: re.Match, ctx: ElclContext, error_message=""):
    """
    Dummy error handler for easier debugging.
    """
    yield from yield_error(lexer, match.pos, match.group(0), error_message)
    ctx.pos = match.end()


RE_END_OF_LINE = r"""(?x)
    ( [ \t]* )                               # Optional spacing.
    ( \# [^\x00-\x08\x0A-\x1F\x7F-\x9F]* )?  # Optional comment.
    ( \n | \r\n )                            # Line break.
"""
RE_SPACING = r"[ \t]+"


class ErbslandConfigurationLanguage(ExtendedRegexLexer):
    """
    Simplified version of the Erbsland Configuration Language.

    The goal of this lexer is to provide useful syntax highlighting for ECL, with a few important checks to
    prevent common mistakes when writing configuration files for this language. Yet, these checks are far from
    complete.
    """

    name = "Erbsland Configuration Language"
    aliases = ["erbsland-conf", "elcl"]
    filenames = ["*.elcl"]
    mimetypes = ["application/erbsland-conf"]
    url = "https://erbsland.dev/"
    version_added = "2.18.1"

    flags = re.DOTALL

    META_BEGIN_UNIQUE = ["@version", "@features", "@signature"]
    META_ANYWHERE = ["@include"]
    META_PARSER = "@parser_"

    RE_TIME_PARTIAL_OFFSET = re.compile(r"\d{2}:\d{2}:\d{2}[-+]\d{2}$")

    BYTE_COUNT_FACTORS = {
        "kb": int(1e3),
        "mb": int(1e6),
        "gb": int(1e9),
        "tb": int(1e12),
        "pb": int(1e15),
        "eb": int(1e18),
        "kib": 2**10,
        "mib": 2**20,
        "gib": 2**30,
        "tib": 2**40,
        "pib": 2**50,
        "eib": 2**60,
    }

    def __init__(
        self,
        error_tracing_enabled=False,
        accept_all_signatures=True,
        error_tracing_callback: Callable[[int, Any, str, ElclContext], None] = None,
        **options,
    ):
        """

        :param error_tracing_enabled: Raise an exception on errors if enabled.
        :param accept_all_signatures: Accept all signatures (for syntax highlighting).
        :param error_tracing_callback: A callback, called for each token,
        """
        super().__init__(**options)
        self.error_tracing_enabled = error_tracing_enabled
        self.error_tracing_callback = error_tracing_callback
        self.accept_all_signatures = accept_all_signatures
        self.last_root: Value | None = None

    def get_value_tree(self, text: str) -> Value:
        """
        Try to parse the given text and return the root of the value tree.

        :raises: DocumentError if there was any error during parsing.
        """
        try:
            for pos, token_type, token_text in self.get_tokens_unprocessed(text):
                if token_type is Error:
                    raise DocumentError(pos, token_text, "Failed to parse document.")
            self.last_root.type = ValueType.DOCUMENT
            return self.last_root
        except InternalError as error:
            raise DocumentError(0, "", str(error))

    def get_tokens_unprocessed(self, text=None, context=None):
        context = ElclContext(text, 0)
        for token in super().get_tokens_unprocessed(text, context):
            if self.error_tracing_callback:
                pos, token_type, text = token
                self.error_tracing_callback(pos, token_type, text, context)
            yield token
        if context.open_states:
            if context.open_states[-1] == OpenState.NAME:
                yield context.pos, Error, f"Name or text with no value at end of document."
            else:
                yield context.pos, Error, f'Unmatched open "{context.open_states[-1]}"'
        self.last_root = context.root

    def yield_groups(self, match: re.Match, tokens: list[Token]):
        group_count = len(match.groups())
        for i, action in enumerate(tokens):
            if i >= group_count:
                return
            data = match.group(i + 1)
            if data:
                if action is Error:
                    yield from yield_error(self, match.start(i + 1), data)
                else:
                    yield match.start(i + 1), action, data

    def section_reset(self, ctx: ElclContext):
        ctx.section = None
        ctx.section_type = SectionType.MAP
        ctx.section_is_relative = False
        ctx.section_name_parts = []
        ctx.value = None

    def section_start(self, match: re.Match, ctx: ElclContext):
        self.section_reset(ctx)
        ctx.section_type = SectionType.LIST if ("*" in match.group(1)) else SectionType.MAP
        ctx.section_is_relative = match.group(4) == "."
        try:
            # If a name has still no value at this point, raise an error
            if ctx.open_states:
                raise InternalError("There is something missing from previous lines.")
            # A document must not start with a relative section.
            if ctx.section_is_relative and ctx.absolute_section is None:
                raise InternalError("A document must not start with a relative section.")
            yield from self.yield_groups(match, [Operator, Punctuation, Whitespace, Operator])
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))
        finally:
            ctx.open_state(OpenState.SECTION)

    def section_error(self, match: re.Match, ctx: ElclContext):
        self.section_reset(ctx)
        yield from handle_error(self, match, ctx)

    def section_name_part(self, match: re.Match, ctx: ElclContext):
        name = match.group(1)
        after_section_end = match.group(5)
        is_continued = bool(match.group(4))  # Relative section indicator
        is_section_end = bool(match.group(3))  # Section header end indicator
        is_text = name.startswith('"')
        try:
            if not ctx.section_error_message:
                name = normalize_name(name)
                self._validate_name(ctx, name, is_text, is_continued)
                self._add_section_name_part(ctx, name)
                if is_section_end:
                    self._finalize_section_header(ctx)
                    if ctx.section_type == SectionType.MAP and after_section_end and "*" in after_section_end:
                        raise InternalError('You can not add "*" to the end of a map section.')
        except InternalError as error:
            if not ctx.section_error_message:
                ctx.section_error_message = str(error)
                ctx.section = Value(f"#error", ValueType.SECTION_WITH_NAMES, ctx.root)
        yield from self._yield_result(match, ctx, is_text)
        if is_section_end:
            ctx.close_state()
            ctx.section_error_message = ""
            ctx.stack.pop()
        ctx.pos = match.end()

    def _validate_name(self, ctx: ElclContext, name: str, is_text: bool, is_continued: bool):
        if ctx.section_is_relative and ctx.absolute_section is None:
            raise InternalError("You cannot start a document with a relative section.")
        if is_text and is_continued:
            raise InternalError("Text names must be the last element in the name path.")
        if name == '""':
            raise InternalError("Empty text is not allowed as text name.")

    def _add_section_name_part(self, ctx: ElclContext, name: str):
        ctx.section_name_parts.append(name)
        if len(ctx.section_name_parts) > 10:
            raise InternalError("A name path must not exceed 10 elements.")

    def _finalize_section_header(self, ctx: ElclContext):
        name_path = ctx.absolute_section.path if ctx.section_is_relative else []
        name_path.extend(ctx.section_name_parts)
        self._validate_path(name_path)
        ctx.section = ctx.root.value_by_path(name_path)
        if ctx.section:
            self._handle_existing_section(ctx)
        else:
            self._create_new_section(ctx, name_path)
        if not ctx.section_is_relative:
            if ctx.section_type == SectionType.LIST:
                # For lists, the absolute section is the list itself, not the first list entry.
                ctx.absolute_section = ctx.section.parent
            else:
                ctx.absolute_section = ctx.section

    def _validate_path(self, name_path: list[str]):
        if len(name_path) > 10:
            raise InternalError("A name path must not exceed 10 elements.")
        if any(name == "" for name in name_path):
            raise InternalError("Empty element in name path.")
        for name in name_path[:-1]:
            if name.startswith('"'):
                raise InternalError("Text names must be the last element in the name path.")

    def _handle_existing_section(self, ctx: ElclContext):
        if ctx.section_type == SectionType.LIST and ctx.section.type == ValueType.SECTION_LIST:
            # Append a new map to the section list
            new_entry = Value("", ValueType.SECTION_WITH_NAMES, ctx.section)
            ctx.section = new_entry
            return
        if (ctx.section_type == SectionType.MAP and ctx.section.type == ValueType.SECTION_LIST) or (
            ctx.section_type == SectionType.LIST and ctx.section.type.is_map()
        ):
            raise InternalError("You cannot mix section lists with regular sections.")
        if not ctx.section.type.is_map():
            raise InternalError("There is already a value with the same name as this section.")
        if ctx.section.type != ValueType.INTERMEDIATE_SECTION:
            raise InternalError("A section with this name was already defined before.")
        # If the section exists, but wasn't defined in the document, use it and mark it as defined.
        ctx.section.type = ValueType.SECTION_WITH_NAMES

    def _create_new_section(self, ctx: ElclContext, name_path: list[str]):
        name = name_path[-1]
        is_text_name = name.startswith('"')
        if ctx.section_type == SectionType.MAP:
            self._create_new_section_map(ctx, name_path, name, is_text_name)
        else:
            if is_text_name:
                raise InternalError("Section lists must not use text names.")
            self._create_new_section_list(ctx, name_path, name)

    def _create_new_section_map(
        self,
        ctx: ElclContext,
        name_path: list[str],
        name: str,
        is_text_name: bool = False,
    ):
        """Handle the case of a new section map."""
        if len(name_path) > 1:
            parent_map = ctx.root.create_missing_maps(name_path[:-1])
        else:
            parent_map = ctx.root
            if is_text_name:
                # Coverage: This error should be handles earlier.
                raise InternalError("You cannot add text names at the document root.")
        # Check for text and regular name mix
        is_text_map = parent_map.type == ValueType.SECTION_WITH_TEXTS
        if parent_map.is_empty():
            # If the section is empty, it can switch from regular names to text names once.
            if is_text_name and not is_text_map:
                parent_map.type = ValueType.SECTION_WITH_TEXTS
        else:
            if is_text_name != is_text_map:
                raise InternalError("You cannot mix text names with regular names.")
            if is_text_name and is_text_map and parent_map.has_values():
                raise InternalError("You cannot mix values and sections with text names under one section.")
        ctx.section = Value(name, ValueType.SECTION_WITH_NAMES, parent_map)

    def _create_new_section_list(self, ctx: ElclContext, name_path: list[str], name: str):
        """Handle the case of a new section list."""
        ctx.section = ctx.root.value_by_path(name_path)
        if ctx.section is None:
            # No section list under the given name, create the required parents and the list itself.
            if len(name_path) > 1:
                parent_container = ctx.root.create_missing_maps(name_path[:-1])
            else:
                parent_container = ctx.root
            ctx.section = Value(name, ValueType.SECTION_LIST, parent_container)
        # Append the new section as element to the list.
        ctx.section = Value("", ValueType.SECTION_WITH_NAMES, ctx.section)

    def _yield_result(self, match, ctx, is_text):
        if self.error_tracing_enabled and ctx.section_error_message:
            yield from handle_error(self, match, ctx, ctx.section_error_message)
        else:
            yield from self.yield_groups(
                match,
                [
                    (Error if ctx.section_error_message else (String.Single if is_text else Name.Tag)),
                    Whitespace,
                    Operator,
                    Operator,
                    Error if ctx.section_error_message else Operator,
                    Whitespace,
                ],
            )

    def process_value_name(self, match: re.Match, ctx: ElclContext):
        try:
            name = match.group(0)
            if ctx.open_states:  # The previous name got no value yet?
                error_state = ctx.open_states[-1]
                ctx.close_state()
                raise InternalError(f"The was no value after the last value separator. (open state={error_state})")
            ctx.indent_pattern = None  # Reset the indent pattern.
            ctx.open_state(OpenState.NAME)  # open until we get a value
            name = normalize_name(name)
            if name.startswith("@"):
                name_type = NameType.META
            elif name.startswith('"'):
                name_type = NameType.TEXT
                if name == '""':
                    raise InternalError("An empty text name is not allowed.")
            else:
                name_type = NameType.REGULAR
            section = ctx.section or ctx.root
            if name_type != NameType.META and section is ctx.root:
                raise InternalError("Values cannot be defined outside a section.")
            v = section.value(name)
            if v is not None and name != "@include":
                display_name = name
                if display_name.startswith('"'):
                    display_name = name[1:-1]
                raise InternalError(f'A {name_type} name "{display_name}" already exists in this section.')
            if not section.is_empty():
                if section.type == ValueType.SECTION_WITH_NAMES and name_type == NameType.TEXT:
                    raise InternalError("Found a text name in a section that contains names.")
                if section.type == ValueType.SECTION_WITH_TEXTS and name_type != NameType.TEXT:
                    raise InternalError("Found a regular name in a section that contains text names.")
            token = Name.Variable
            if name_type == NameType.META:
                token = self._process_meta_name(name, ctx)
            # Everything is ok! add a new value to the section.
            ctx.value = Value(name, ValueType.UNDEF, section)
            yield match.start(), token, match.group(0)
            ctx.pos = match.end()
        except InternalError:
            ctx.value = Value("???", ValueType.UNDEF)
            yield from handle_error(self, match, ctx)

    def _process_meta_name(self, name: str, ctx: ElclContext):
        token = Name.Builtin
        if name in self.META_BEGIN_UNIQUE:
            if ctx.root.has_sections() or ctx.root.value(name):
                raise InternalError("Meta value must be before the first section.")
            if not self.accept_all_signatures and name == "@signature":
                raise InternalError("Signature not supported.")
            ctx.value = Value(f"@{name}", ValueType.UNDEF, ctx.root)
        elif name in self.META_ANYWHERE:
            token = Name.Function  # ignore includes.
        elif name.startswith(self.META_PARSER):
            token = Name.Attribute  # ignore parser values.
        else:
            raise InternalError("Unknown meta value or command.")
        return token

    def _value_processed(self, ctx: ElclContext):
        if ctx.open_states and ctx.open_states[-1] == OpenState.NAME:  # After we get a value, close the open name.
            ctx.close_state()

    def process_value_on_next_line(self, match: re.Match, ctx: ElclContext):
        """For a value on the next line, capture the indent pattern."""
        ctx.indent_pattern = match.group(0)
        yield match.start(), Whitespace, match.group(0)
        ctx.pos = match.end()

    def process_comma(self, match: re.Match, ctx: ElclContext):

        pass  # FIXME

        tokens = [Whitespace, Operator, Whitespace]
        if len(match.groups()) > 3:
            tokens.extend([Comment, Whitespace])
        yield from self.yield_groups(match, tokens)
        ctx.pos = match.end()

    def _process_integer_value(self, match: re.Match, ctx: ElclContext, format: str, max_digits: int):
        self._value_processed(ctx)
        text = match.group(0).replace("'", "").lstrip("+")  # Remove digit separators and leading plus
        base = 10
        token = Number.Integer
        if format == "hex":
            base = 16
            token = Number.Hex
            text = text.lower().replace("0x", "")  # Remove prefix
        elif format == "bin":
            base = 2
            token = Number.Bin
            text = text.lower().replace("0b", "")  # Remove prefix
        try:
            if len(text.lstrip("-")) > max_digits:
                raise InternalError("Too many digits for this number.")
            try:
                if format == "bin" and len(text) == max_digits and text[0] == "1":  # Binary negative sign
                    value = int(text, base) - (1 << max_digits)  # Convert it into a negative number.
                else:
                    value = int(text, base)
                if format == "dec" and value != 0 and text.startswith(("0", "-0")):
                    raise InternalError("Zero prefix is not allowed")
                if value >= 0 and value.bit_length() > 63:
                    raise InternalError("The number exceeds the valid number range.")
                if value < 0 and (abs(value) - 1).bit_length() > 63:
                    raise InternalError("The negative number exceeds the valid number range.")
            except ValueError as error:
                raise InternalError(
                    f"The number must be an integer. "
                    f'Tried to parse "{text}" from original "{match.group(0)}". '
                    f"Error: {error}"
                )
            ctx.value.type = ValueType.INTEGER
            ctx.value.data = value
            yield match.start(), token, match.group(0)
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_dec_value(self, match: re.Match, ctx: ElclContext):
        yield from self._process_integer_value(match, ctx, "dec", 19)

    def process_hex_value(self, match: re.Match, ctx: ElclContext):
        yield from self._process_integer_value(match, ctx, "hex", 16)

    def process_bin_value(self, match: re.Match, ctx: ElclContext):
        yield from self._process_integer_value(match, ctx, "bin", 64)

    def process_float_value(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        # Remove digit separators and leading plus
        text = match.group(0).replace("'", "").lstrip("+").lower()
        try:
            try:
                mantissa_part = slice(0, text.index("e")) if "e" in text else slice(0, len(text))
                if sum(1 for c in text[mantissa_part] if c.isdigit()) > 20:
                    raise InternalError("Too many digits for this number.")
                if "e" in text and len(text[text.index("e") :].strip("e+-")) > 6:
                    raise InternalError("Too many digits in the exponent.")
                value = float(text)
                if "." in text:
                    int_text = text[: text.index(".")]
                elif "e" in text:
                    int_text = text[: text.index("e")]
                else:
                    int_text = text
                int_text = int_text.lstrip("-")
                if len(int_text) > 1 and int_text.startswith("0"):
                    raise InternalError("Zero prefix is not allowed")
            except ValueError:
                raise InternalError("This is no valid floating point number.")
            ctx.value.type = ValueType.FLOAT
            ctx.value.data = value
            yield match.start(), Number.Float, match.group(0)
            ctx.pos = match.end()
        except InternalError:
            yield from handle_error(self, match, ctx)

    def process_bool_value(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        data = match.group(0).lower() in ["true", "yes", "enabled", "on"]
        ctx.value.type = ValueType.BOOLEAN
        ctx.value.data = data
        yield match.start(), Keyword.Constant, match.group(0)
        ctx.pos = match.end()

    def process_date_value(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        dt_text = str(match.group(0).upper())  # Upper for python time parsing.
        try:
            if self.RE_TIME_PARTIAL_OFFSET.match(dt_text):
                dt_text += ":00"  # Python does not support partial time offsets.
            dt_text = dt_text.lstrip("T")
            if len(dt_text) > 10 and dt_text[4] == "-":
                ctx.value.data = datetime.datetime.fromisoformat(dt_text)
                ctx.value.type = ValueType.DATETIME
            elif dt_text[2] == ":":
                ctx.value.data = datetime.time.fromisoformat(dt_text)
                ctx.value.type = ValueType.TIME
            else:
                ctx.value.data = datetime.date.fromisoformat(dt_text)
                ctx.value.type = ValueType.DATE
            yield match.start(), Literal.Date, match.group(0)
            ctx.pos = match.end()
        except ValueError as error:
            yield from handle_error(self, match, ctx, f"The date/time value is not valid. Error: {error}")

    def _get_token_for_state(self, state: OpenState):
        match state:
            case OpenState.TEXT:
                return String.Double
            case OpenState.MULTILINE_TEXT:
                return String.Double
            case OpenState.CODE:
                return String.Backtick
            case OpenState.MULTILINE_CODE:
                return String.Backtick
            case OpenState.REGEX:
                return String.Regex
            case OpenState.MULTILINE_REGEX:
                return String.Regex
            case OpenState.BYTE_DATA:
                return String.Single
            case OpenState.MULTILINE_BYTE_DATA:
                return String.Single
        return String

    def _process_generic_text_start(self, match: re.Match, ctx: ElclContext, state: OpenState, value_type: ValueType):
        self._value_processed(ctx)
        ctx.open_state(state)
        if ctx.value:
            ctx.value_text = ""
            ctx.value.type = value_type
        token = self._get_token_for_state(ctx.open_states[-1])
        if state == OpenState.MULTILINE_CODE:
            yield from self.yield_groups(match, [token, String.Affix])
        else:
            yield match.start(), token, match.group(0)
        ctx.pos = match.end()

    def process_text_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.TEXT, ValueType.TEXT)

    def process_code_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.CODE, ValueType.TEXT)

    def process_regex_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.REGEX, ValueType.REGEX)

    def process_text_char(self, match: re.Match, ctx: ElclContext):
        ctx.value_text += match.group(0)
        yield match.start(), String.Double, match.group(0)
        ctx.pos = match.end()

    def process_text_escape(self, match: re.Match, ctx: ElclContext):
        escape_text = match.group(1).lower()
        try:
            if escape_text in TEXT_ESCAPE_SUBSTITUTIONS:
                ctx.value_text += TEXT_ESCAPE_SUBSTITUTIONS[escape_text]
            elif escape_text.startswith("u"):
                try:
                    if escape_text[1] == "{":
                        code = int(escape_text[2:-1], 16)
                    else:
                        code = int(escape_text[1:], 16)
                except ValueError:
                    yield from handle_error(self, match, ctx)
                    return
                if code <= 0 or (0xD800 <= code <= 0xDFFF) or code > 0x10FFFF:
                    raise InternalError(f"Invalid unicode escape code point 0x{code:x}.")
                ctx.value_text += chr(code)
            else:
                raise InternalError(f"Unknown escape sequence {escape_text}")
            yield match.start(), String.Escape, match.group(0)
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_text_end(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Unexpected text end, with no value prepared.")
            ctx.value.data = ctx.value_text
            # If we just read a meta 'version' value with a version != 1.0, rise an error.
            if ctx.value.type == ValueType.TEXT and ctx.value.name == "@version" and ctx.value_text != "1.0":
                raise InternalError("Unsupported language version number.")
            yield match.start(), self._get_token_for_state(ctx.open_states[-1]), match.group(0)
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))
        finally:
            ctx.value_text = ""
            ctx.indent_pattern = None
            ctx.close_state()

    def process_multi_line_text_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.MULTILINE_TEXT, ValueType.TEXT)

    def process_multi_line_code_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.MULTILINE_CODE, ValueType.TEXT)

    def process_multi_line_regex_start(self, match: re.Match, ctx: ElclContext):
        yield from self._process_generic_text_start(match, ctx, OpenState.MULTILINE_REGEX, ValueType.REGEX)

    def process_after_multi_line_start(self, match: re.Match, ctx: ElclContext):
        try:
            indentation = match.group(4)
            if not ctx.indent_pattern:
                # Store the initial indent pattern, if this wasn't already done before.
                ctx.indent_pattern = indentation
            elif not indentation.startswith(ctx.indent_pattern):
                raise InternalError("Indentation pattern after opening sequence does not match.")
            if match.group(1):
                yield match.start(1), Whitespace, match.group(1)
            if match.group(2):
                yield match.start(2), Comment, match.group(2)
            if match.group(3):
                yield match.start(3), Whitespace, match.group(3)
            yield match.start(4), Whitespace, ctx.indent_pattern
            ctx.pos = match.start(4) + len(ctx.indent_pattern)
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_multi_line_text(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Multi-line text in the wrong state")
            ctx.value_text += match.group(0)
            yield match.start(), self._get_token_for_state(ctx.open_states[-1]), match.group(0)
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_multi_line_spacing(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Multi-line spacing in the wrong state")
            if not match.group(2):  # Do not add trailing spacing.
                ctx.value_text += match.group(1)
            yield match.start(), self._get_token_for_state(ctx.open_states[-1]), match.group(0)
            ctx.pos = match.end(1)
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_multi_line_line_break(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Multi-line line-break in the wrong state")
            if len(match.groups()) > 2:
                indentation = None  # Empty line
            elif len(match.groups()) == 2 and match.group(2) is not None:
                indentation = match.group(2)
            else:
                indentation = None
            if indentation:
                if not ctx.indent_pattern:
                    ctx.indent_pattern = indentation
                elif not indentation.startswith(ctx.indent_pattern):
                    raise InternalError("Indentation pattern on continued line does not match.")
                ctx.value_text += "\n"
                # Only move the position up to the level of the indentation pattern.
                text = match.group(1) + match.group(2)[: len(ctx.indent_pattern)]
                yield match.start(), Whitespace, text
                ctx.pos = match.start() + len(text)
            else:
                yield match.start(), Whitespace, match.group(0)
                ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_multi_line_end(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Multi-line end in the wrong state")
            if len(match.groups()) == 3:
                indentation = match.group(2)
            else:
                indentation = match.group(4)
            if not ctx.indent_pattern:
                ctx.indent_pattern = indentation
            elif not indentation.startswith(ctx.indent_pattern):
                raise InternalError("Indentation pattern before closing sequence does not match.")
            if indentation != ctx.indent_pattern:
                # This is not the end of the text.
                if len(match.groups()) == 3:
                    if match.group(1):
                        yield match.start(1), Whitespace, match.group(1)
                    yield match.start(2), Whitespace, ctx.indent_pattern
                    ctx.pos = match.start(2) + len(ctx.indent_pattern)
                else:
                    if match.group(1):
                        yield match.start(1), Whitespace, match.group(1)
                    if match.group(2):
                        yield match.start(2), Comment, match.group(1)
                    if match.group(3):
                        yield match.start(3), Whitespace, match.group(1)
                    ctx.pos = match.start(4) + len(ctx.indent_pattern)
                return
            ctx.value.data = ctx.value_text
            if len(match.groups()) == 3:
                yield from self.yield_groups(
                    match,
                    [
                        Whitespace,
                        Whitespace,
                        self._get_token_for_state(ctx.open_states[-1]),
                    ],
                )
            else:
                yield from self.yield_groups(
                    match,
                    [
                        Whitespace,
                        Comment,
                        Whitespace,
                        Whitespace,
                        self._get_token_for_state(ctx.open_states[-1]),
                    ],
                )
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))
        ctx.value_text = ""
        ctx.indent_pattern = None
        ctx.close_state()
        ctx.stack.pop()

    def process_byte_data_start(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        try:
            if ctx.value:
                ctx.value_data = b""
                ctx.value.type = ValueType.BYTES
                ctx.value.data = b""
            if match.group(1) == "<<<":
                ctx.open_state(OpenState.MULTILINE_BYTE_DATA)
            else:
                ctx.open_state(OpenState.BYTE_DATA)
            yield from self.yield_groups(match, [String.Single, String.Affix])
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_byte_data_byte(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Byte-data in the wrong state")
            ctx.value_data += bytes.fromhex(match.group(0))
            yield match.start(), Number.Hex, match.group(0)
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def _handle_byte_data_line_break(self, match: re.Match, ctx: ElclContext):
        if match.group(1):
            yield match.start(1), Whitespace, match.group(1)  # Optional spacing at end of line
        if match.group(2):
            yield match.start(2), Comment, match.group(2)  # Optional comment
        yield match.start(3), Whitespace, match.group(3)  # Line-break
        if len(match.groups()) >= 4:
            yield match.start(4), Whitespace, ctx.indent_pattern  # Indent pattern
            # Only move the position up to the level of the indentation pattern.
            ctx.pos = match.start(4) + len(ctx.indent_pattern)
        else:  # Empty line
            ctx.pos = match.end()

    def process_byte_data_line_break(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Byte-data line-break in the wrong state")
            if len(match.groups()) >= 4:  # Only test indentation if this isn't an empty line.
                indentation = match.group(4)
                if not ctx.indent_pattern:
                    ctx.indent_pattern = indentation
                elif not indentation.startswith(ctx.indent_pattern):
                    raise InternalError("Indentation pattern on continued line does not match.")
            yield from self._handle_byte_data_line_break(match, ctx)
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_byte_data_end(self, match: re.Match, ctx: ElclContext):
        try:
            if not ctx.value:
                raise InternalError("Byte-data in the wrong state")
            if ctx.open_states[-1] == OpenState.MULTILINE_BYTE_DATA:
                indentation = match.group(4)
                if ctx.indent_pattern:  # Only test the indent pattern if we got one.
                    if not indentation.startswith(ctx.indent_pattern):
                        raise InternalError("Indentation pattern on continued line does not match.")
                    if indentation != ctx.indent_pattern:  # This is not the end, just a regular line.
                        yield from self._handle_byte_data_line_break(match, ctx)
                        return
                yield from self.yield_groups(match, [Whitespace, Comment, Whitespace, Whitespace, String.Single])
            else:
                yield match.start(), String.Single, match.group(0)
            ctx.value.data = ctx.value_data
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))
        ctx.value_data = b""
        ctx.indent_pattern = None
        ctx.close_state()

    def _convert_integer(self, original_text: str):
        text = original_text.replace("'", "").lstrip("+")  # Remove digit separators and leading plus
        if len(text.lstrip("-")) > 19:
            raise InternalError("Too many digits for this number.")
        try:
            value = int(text)
            if value != 0 and text.startswith(("0", "-0")):
                raise InternalError("Zero prefix is not allowed")
        except ValueError as error:
            raise InternalError(
                f"The number must be an integer. "
                f'Tried to parse "{text}" from original "{original_text}". '
                f"Error: {error}"
            )
        return value

    def process_byte_count(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        try:
            value = self._convert_integer(match.group(1))
            suffix = match.group(3).lower()
            if suffix not in self.BYTE_COUNT_FACTORS:
                raise InternalError("This byte count exceeds the valid number range.")
            value *= self.BYTE_COUNT_FACTORS[suffix]
            if value >= 0 and value.bit_length() > 63:
                raise InternalError("The number exceeds the valid number range.")
            if value < 0 and (abs(value) - 1).bit_length() > 63:
                raise InternalError("The negative number exceeds the valid number range.")
            ctx.value.type = ValueType.INTEGER
            ctx.value.data = value
            yield from self.yield_groups(match, [Number.Integer, Whitespace, Keyword.Type])
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    def process_time_delta(self, match: re.Match, ctx: ElclContext):
        self._value_processed(ctx)
        try:
            value = self._convert_integer(match.group(1))
            suffix = match.group(3).lower()
            ctx.value.type = ValueType.TIME_DELTA
            ctx.value.data = (value, suffix)
            yield from self.yield_groups(match, [Number.Integer, Whitespace, Keyword.Type])
            ctx.pos = match.end()
        except InternalError as error:
            yield from handle_error(self, match, ctx, str(error))

    tokens = {
        "root": [
            (RE_END_OF_LINE, bygroups(Whitespace, Comment, Whitespace)),
            # Error handling: Mark the whole section as error for better effect.
            (
                r"""(?x)
                    -* \*? \[ (?:                      # Section start
                        (?: [ \t] | \. )*              #   Error: No actual content
                    |
                        [ \t]* " [^\]]+?               #   Error: Starts with text value.
                    ) \] \*? -*                        # Section end
                """,
                section_error,
                "line_end",
            ),
            # Section Start
            (r"(-*\*?)(\[)([ \t]*)(\.)?", section_start, ("line_end", "section_names")),
            # Named value or meta value
            (r"(?i)(?=@?[a-z\"])", Whitespace, "value_name"),
            # Error handling for ctrl characters.
            (r"[\x00-\x08\x0A-\x1F\x7F-\x9F]+", handle_error),
        ],
        "section_names": [
            (RE_SPACING, Whitespace),
            # Name/Text, Section End/Name Separator
            (
                r"""(?xi)
                (                                             # (1)
                    [a-z][a-z0-9]*(?:[ _][a-z0-9]+)*          # Name
                |                                             # or
                    " (?: \\                                  # Text start with double quote
                        (?: [\\"$nrt] | u (?:                 #   Handle an escape sequence
                            [a-fA-F0-9]{4} |
                            \{ [a-fA-F0-9]{1,8} \}
                        ) )
                    |
                        [^\x00-\x08\x0A-\x1F\x7F-\x9F\\"]+   #   Or any non-reserved, non-control character
                    )* "                                      # Text end with double quote
                )  
                ( [ \t]* )                                    # (2) Optional spacing
                (?: (\]) | (\.) )                             # (3)(4) Name separator or section end
                (?(3)                                         # If section end ... 
                    (\*? -*)                                  # (5) Match optional star and dash
                    |                                         # ... else ...
                    ([ \t]*)                                  # (6) Optional whitespace 
                )                    
                """,
                section_name_part,
            ),
        ],
        "value_name": [
            # Name, Meta Name or Text
            (
                r"""(?xi)
                    (?:                                            # (1)
                        @?[a-z][a-z0-9]*(?:[ _][a-z0-9]+)*         # Name or Meta Name
                    |                                              # or
                        " (?: \\                                   # Text start with double quote
                            (?: [\\"$nrt] | u (?:                  #   Handle an escape sequence
                                [a-fA-F0-9]{4} |
                                \{ [a-fA-F0-9]{1,8} \}
                            ) )
                        |
                            [^\x00-\x08\x0A-\x1F\x7F-\x9F\\"]+     #   Or any non-reserved, non-control character
                        )* "                                       # Text end with double quote
                    )
                """,
                process_value_name,
                ("#pop", "value_after_name", "value_separator"),
            ),
        ],
        "value_separator": [
            (RE_SPACING, Whitespace),
            # Separator
            (r"[:=]", Operator, "#pop"),
        ],
        "line_end": [
            (RE_END_OF_LINE, bygroups(Whitespace, Comment, Whitespace), "#pop"),
        ],
        "value_after_name": [
            # Empty Line (optional comment)
            (
                RE_END_OF_LINE,
                bygroups(Whitespace, Comment, Whitespace),
                ("#pop", "value_on_next_line"),
            ),
            # Ignore optional spacing and expect a value.
            (r"[ \t]*", Whitespace, ("#pop", "comma_list", "single_value")),
        ],
        "value_on_next_line": [  # Possible value on the next line, or undefined value.
            # Empty line => back to root.
            (RE_END_OF_LINE, bygroups(Whitespace, Comment, Whitespace), "#pop:2"),
            # Name or section => back to root.
            (r"(?=[^ \t])", Whitespace, "#pop:2"),
            # Line List
            (r"(?=[ \t]+\*)", Whitespace, ("#pop", "line_list")),
            # Indent => Value on the next line.
            (
                r"[ \t]+(?!\*)",
                process_value_on_next_line,
                ("#pop", "comma_list", "single_value"),
            ),
        ],
        "line_list": [
            # Continued List
            (
                r"([ \t]+)(\*)([ \t]*)",
                bygroups(Whitespace, Operator, Whitespace),
                ("comma_list", "single_value"),
            ),
            # If there is anything else, back to root.
            (r"(?=.)", Whitespace, "#pop"),
        ],
        "comma_list": [
            # Empty line => end of list.
            (RE_END_OF_LINE, bygroups(Whitespace, Comment, Whitespace), "#pop"),
            (  # Early catch the error with a trailing comma.
                r"""(?x)
                    ( [ \t]* )                               # Optional spacing.
                    ( , )                                    # Trailing comma.
                    ( [ \t]* )                               # Optional spacing.
                    ( \# [^\x00-\x08\x0A-\x1F\x7F-\x9F]* )?  # Optional comment.
                    ( \n | \r\n )                            # Line break.
                """,
                bygroups(Whitespace, Error, Whitespace, Comment, Whitespace),
                "#pop",
            ),
            (  # If we get a comma after the value, and something else, expect another value.
                r"""(?x)
                ( [ \t]* )
                ( , )
                ( [ \t]* )
                """,
                process_comma,
                ("#pop", "comma_list", "single_value"),
            ),
        ],
        "single_value": [
            (
                r",",
                handle_error,
                "#pop",
            ),  # Early catch common errors with starting comma or consecutive ones.
            include("boolean"),
            include("date_time"),
            include("float"),
            include("date_time"),
            include("byte_counts"),
            include("time_deltas"),
            include("integer"),
            include("text_multi_line_start"),
            include("text_start"),
            include("code_multi_line_start"),
            include("code_start"),
            include("regex_multi_line_start"),
            include("regex_start"),
            include("byte_data_multi_line_start"),
            include("byte_data_start"),
        ],
        "boolean": [
            (
                r"(?i)(true|false|yes|no|enabled|disabled|on|off)",
                process_bool_value,
                "#pop",
            ),
        ],
        "integer": [
            (
                r"""(?xi)
                [-+]?                                    # Positive or negative sign
                0x                                       # Hex prefix
                (?: [a-f0-9]+ \u0027 )* [a-f0-9]+        # Hex digits groups, optional '
                """,
                process_hex_value,
                "#pop",
            ),
            (
                r"""(?xi)
                [-+]?                                    # Positive or negative sign
                0b                                       # Binary prefix
                (?: [01]+ \u0027 )* [01]+                # Binary digits groups, optional '
                """,
                process_bin_value,
                "#pop",
            ),
            (
                r"""(?xi)
                [-+]?                                    # Positive or negative sign
                (?: \d+ \u0027 )* \d+                    # Integer digits groups, optional '
                """,
                process_dec_value,
                "#pop",
            ),
        ],
        "float": [
            (
                r"""(?xi)
                [-+]?
                (?: inf | nan )
                """,
                process_float_value,
                "#pop",
            ),
            (
                r"""(?xi)
                [-+]?                                      # Positive or negative sign.
                (?:
                    (?:                                    # [X].Y[E+Z] notation.
                        (?: (?: \d+ \u0027 )* \d+ )? \. (?: \d+ \u0027 )* \d+
                    |                                      # X.[Y][E+Z] notation.
                        (?: \d+ \u0027 )* \d+ \. (?: (?: \d+ \u0027 )* \d+ )?
                    )
                    (?:
                        e[-+]? \d+
                    )?
                |                                          # XE+Z notation.
                    (?: \d+ \u0027 )* \d+
                    e[-+]? \d+
                )
                """,
                process_float_value,
                "#pop",
            ),
        ],
        "date_time": [
            (
                r"""(?ix)
                (
                    \d{4} - (?: 0[1-9] | 1[0-2] ) - (?: 0[1-9] | [12]\d | 3[01] )
                    [ t]?
                    (?: [01]\d | 2[0-3] ) : ( [0-5]\d )
                    (?: : [0-5]\d (?: \. \d{1,9} )? )?
                    (?: z | [-+] (?: [01]\d | 2[0-3] ) (?: : [0-5]\d )? )?
                |
                    \d{4} - (?: 0[1-9] | 1[0-2] ) - (?: 0[1-9] | [12]\d | 3[01] )
                |
                    t?
                    (?: [01]\d | 2[0-3] ) : (?: [0-5]\d )
                    (?: : [0-5]\d (?: \. \d{1,9} )? )?
                    (?: z | [-+] (?: [01]\d | 2[0-3] ) (?: : [0-5]\d )? )?
                )
                """,
                process_date_value,
                "#pop",
            ),
        ],
        "byte_counts": [
            (
                r"""(?ix)
                (
                    [-+]?                                # Positive or negative sign
                    (?: \d+ \u0027 )* \d+                # Integer digits with optional '
                )
                ( \x20 )?                                # Optional space between digits and unit
                ( [kmgtpezy] i? b )                      # Iso unit up to yota-bytes
                """,
                process_byte_count,
                "#pop",
            ),
        ],
        "time_deltas": [
            (
                r"""(?ix)
                (
                    [-+]?                                # Positive or negative sign
                    (?: \d+ \u0027 )* \d+                # Integer digits with optional '
                )
                ( \x20 )?                                # Optional space before the unit.
                (
                    nanoseconds? | ns |
                    microseconds? | us | µs |
                    milliseconds? | ms |
                    seconds? | s |
                    minutes? | m |
                    hours? | h |
                    days? | d |
                    weeks? | w |
                    months? |
                    years?
                )
                """,
                process_time_delta,
                "#pop",
            ),
        ],
        "text_start": [
            (r'"', process_text_start, ("#pop", "text")),
        ],
        "text": [
            include("text_escape"),
            # End of text.
            (r'"', process_text_end, "#pop"),
            include("text_placeholder"),
            (r'[^\x00-\x08\x0A-\x1F\x7F-\x9F\\"$]+', process_text_char),
        ],
        "text_multi_line_start": [
            (
                r'"""',
                process_multi_line_text_start,
                ("#pop", "text_multi_line", "text_multi_line_after_start"),
            ),
        ],
        "text_multi_line_after_start": [
            # Handle the special case of an empty line.
            (
                RE_END_OF_LINE + r"(?=[ \t]*\n|\r\n)",
                process_multi_line_line_break,
                "#pop",
            ),
            # Handle the special case of an early end.
            (RE_END_OF_LINE + r'([ \t]+)(""")', process_multi_line_end, "#pop"),
            # Everything else must be content.
            (RE_END_OF_LINE + r"([ \t]+)", process_after_multi_line_start, "#pop"),
        ],
        "multi_line_line_break": [
            (r"(\n|\r\n)([ \t]+)", process_multi_line_line_break),
            (r"(\n|\r\n)(?=\n|\r\n)", process_multi_line_line_break),
        ],
        "text_multi_line": [
            # End of text.
            (
                r'(\n|\r\n)([ \t]+)(""")',
                process_multi_line_end,
            ),  # function will decide if this pops the stack.
            include("multi_line_line_break"),
            include("text_escape"),
            include("text_placeholder"),
            (r"([ \t]+)(\n|\r\n)?", process_multi_line_spacing),
            (r"[^\x00-\x08\x0A-\x1F\x7F-\x9F\\$ \t]+", process_multi_line_text),
        ],
        "text_placeholder": [
            # Just a $ is perfectly valid.
            (r"(?ix) \$ (?!\{)", process_text_char),
            # Empty placeholder is not valid.
            (r"(?ix) \$ \{ \}", handle_error),
            # Placeholder
            (r"(?ix) \$ \{ [-=.: _a-z0-9]+ \}", process_text_char),
            # Open placeholder is not valid.
            (r"(?ix) \$ \{ [-=.: _a-z0-9]*", handle_error),
        ],
        "text_escape": [
            (
                r'(?ix) \\ ( [\\"$nrt] | u (?: [a-f0-9]{4} | \{ [a-f0-9]{1,8} \} ) )',
                process_text_escape,
            ),
        ],
        "code_start": [
            (r"`", process_code_start, ("#pop", "code")),
        ],
        "code": [
            # End of code.
            (r"`", process_text_end, "#pop"),
            (r"[^\x00-\x08\x0A-\x1F\x7F-\x9F`]+", process_text_char),
        ],
        "code_multi_line_start": [
            (
                r"(```)(\w{1,16})?",
                process_multi_line_code_start,
                ("#pop", "code_multi_line", "code_multi_line_after_start"),
            ),
        ],
        "code_multi_line_after_start": [
            # Handle the special case of an empty line.
            (
                RE_END_OF_LINE + r"(?=[ \t]*\n|\r\n)",
                process_multi_line_line_break,
                "#pop",
            ),
            # Handle the special case of an early end.
            (RE_END_OF_LINE + r"([ \t]+)(```)", process_multi_line_end, "#pop"),
            # Everything else must be content.
            (RE_END_OF_LINE + r"([ \t]+)", process_after_multi_line_start, "#pop"),
        ],
        "code_multi_line": [
            # End of code.
            (
                r"(\n|\r\n)([ \t]+)(```)",
                process_multi_line_end,
            ),  # function will decide if this pops the stack.
            include("multi_line_line_break"),
            (r"[^\x00-\x08\x0A-\x1F\x7F-\x9F]+", process_text_char),
        ],
        "regex_start": [
            (r"/", process_regex_start, ("#pop", "regex")),
        ],
        "regex": [
            include("regex_escape"),
            include("regex_special"),
            # End of regex.
            (r"/", process_text_end, "#pop"),
            include("regex_anything"),
        ],
        "regex_multi_line_start": [
            (
                r"(///)([ \t]*)",
                process_multi_line_regex_start,
                ("#pop", "regex_multi_line", "regex_multi_line_after_start"),
            ),
        ],
        "regex_multi_line_after_start": [
            # Handle the special case of an empty line.
            (
                RE_END_OF_LINE + r"(?=[ \t]*\n|\r\n)",
                process_multi_line_line_break,
                "#pop",
            ),
            # Handle the special case of an early end.
            (RE_END_OF_LINE + r"([ \t]+)(///)", process_multi_line_end, "#pop"),
            # Everything else must be content.
            (RE_END_OF_LINE + r"([ \t]+)", process_after_multi_line_start, "#pop"),
        ],
        "regex_multi_line": [
            # End of regex.
            (
                r"(\n|\r\n)([ \t]+)(///)",
                process_multi_line_end,
            ),  # function will decide if this pops the stack.
            (r"/+", String.Regex),
            include("multi_line_line_break"),
            include("regex_escape"),
            include("regex_comment"),
            include("regex_special"),
            include("regex_anything"),
        ],
        "regex_escape": [
            (
                r"""(?x)
                \\ (
                    x[a-fA-F0-9]{2} |
                    u[a-fA-F0-9]{4} |
                    U[a-fA-F0-9]{8} |
                    N\{ [^}]*? \} |
                    [^\x00-\x08\x0A-\x1F\x7F-\x9F]
                )
                """,
                String.Escape,
            ),
        ],
        "regex_comment": [
            (
                r"""(?x)
                ( \# [^\x00-\x08\x0A-\x1F\x7F-\x9F]* )
                (?= \n | \r\n )
                """,
                Comment,
            ),
        ],
        "regex_special": [
            (r"[-.^$*+?]", Operator),
            (r"#", String.Regex),
            (r"[\x28\x29\x5B\x5D\x7B-\x7D]", Punctuation),
        ],
        "regex_anything": [
            (
                r"[^\x00-\x08\x0A-\x1F\x7F-\x9F\\/\x28\x29\x2d\x5B\x5D\x7B-\x7D.^$*+?#]+",
                String.Regexp,
            ),
        ],
        "byte_data_start": [
            (r"(<)(hex:)?", process_byte_data_start, ("#pop", "byte_data")),
        ],
        "byte_data": [
            (RE_SPACING, Whitespace),
            # Hex byte.
            (r"[a-fA-F0-9]{2}", process_byte_data_byte),
            # End of binary.
            (r">", process_byte_data_end, "#pop"),
        ],
        "byte_data_multi_line_start": [
            (
                r"(<<<)(hex)?",
                process_byte_data_start,
                ("#pop", "byte_data_multi_line", "byte_data_after_start"),
            ),
        ],
        "byte_data_after_start": [
            # Handle the special case of an empty line.
            (
                RE_END_OF_LINE + r"(?=[ \t]*\n|\r\n)",
                process_byte_data_line_break,
                "#pop",
            ),
            # Handle the special case of an early end.
            (RE_END_OF_LINE + r"([ \t]+)(>>>)", process_byte_data_end, "#pop:2"),
            # Everything else must be content.
            (RE_END_OF_LINE + r"([ \t]+)", process_byte_data_line_break, "#pop"),
        ],
        "byte_data_multi_line": [
            # Handle the special case of an empty line
            (RE_END_OF_LINE + r"(?=[ \t]*\n|\r\n)", process_byte_data_line_break),
            (RE_END_OF_LINE + r"([ \t]+)(>>>)", process_byte_data_end, "#pop"),
            (RE_END_OF_LINE + r"([ \t]+)", process_byte_data_line_break),
            (RE_SPACING, Whitespace),
            (r"([a-fA-F0-9]{2})", process_byte_data_byte),
        ],
    }

