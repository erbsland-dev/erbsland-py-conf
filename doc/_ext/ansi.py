# -*- coding: utf-8 -*-
# Copyright (c) 2010, Sebastian Wiesner <lunaryorn@googlemail.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


# ErbslandDEV 2025-06-22:
# - Removed outdated code that manually copies a default CSS file.
# - Added a state-based approach that sets and resets the different
#   states of a terminal.
# - Added many missing ANSI codes for better color support.
# - Removed the original CSS file, needs to be user-supplied.


"""
_ext.ansi
=========

This extension parses ANSI color codes in literal blocks.

.. moduleauthor::  Sebastian Wiesner  <lunaryorn@googlemail.com>
"""
import enum
import re

from dataclasses import dataclass
from typing import Optional, Union

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst.directives import single_char_or_unicode


class ansi_literal_block(nodes.literal_block):
    """
    Represent a literal block, that contains ANSI color codes.
    """

    pass


#: the pattern to find ANSI color codes
COLOR_PATTERN: re.Pattern[str] = re.compile(r"\x1b\[([^m]+)m")


class ANSIAttribute(enum.Enum):
    BOLD = enum.auto()
    DIM = enum.auto()
    ITALIC = enum.auto()
    UNDERLINE = enum.auto()
    BLINK = enum.auto()
    REVERSE = enum.auto()
    HIDDEN = enum.auto()
    STRIKE = enum.auto()
    FOREGROUND = enum.auto()
    BACKGROUND = enum.auto()

    def to_class_name(self, value: str) -> str:
        if self == ANSIAttribute.BACKGROUND:
            return f"bg_{value}"
        return value


@dataclass
class ANSIAttributeDefinition:
    attribute: Union[ANSIAttribute, list[ANSIAttribute]]
    value: str


CODE_COLOR_MAP: dict[int, str] = {
    0: "black",
    1: "red",
    2: "green",
    3: "yellow",
    4: "blue",
    5: "magenta",
    6: "cyan",
    7: "white",
}


CODE_ATTRIBUTE_MAP: dict[int, ANSIAttributeDefinition] = {
    0: ANSIAttributeDefinition(
        [
            ANSIAttribute.BOLD,
            ANSIAttribute.DIM,
            ANSIAttribute.ITALIC,
            ANSIAttribute.UNDERLINE,
            ANSIAttribute.BLINK,
            ANSIAttribute.REVERSE,
            ANSIAttribute.HIDDEN,
            ANSIAttribute.STRIKE,
            ANSIAttribute.FOREGROUND,
            ANSIAttribute.BACKGROUND,
        ],
        "",
    ),
    1: ANSIAttributeDefinition(ANSIAttribute.BOLD, "bold"),
    2: ANSIAttributeDefinition(ANSIAttribute.DIM, "dim"),
    3: ANSIAttributeDefinition(ANSIAttribute.ITALIC, "italic"),
    4: ANSIAttributeDefinition(ANSIAttribute.UNDERLINE, "underline"),
    5: ANSIAttributeDefinition(ANSIAttribute.BLINK, "blink"),
    6: ANSIAttributeDefinition(ANSIAttribute.REVERSE, "reverse"),
    7: ANSIAttributeDefinition(ANSIAttribute.HIDDEN, "hidden"),
    8: ANSIAttributeDefinition(ANSIAttribute.STRIKE, "strike"),
    22: ANSIAttributeDefinition([ANSIAttribute.BOLD, ANSIAttribute.DIM], ""),
    23: ANSIAttributeDefinition(ANSIAttribute.ITALIC, ""),
    24: ANSIAttributeDefinition(ANSIAttribute.UNDERLINE, ""),
    25: ANSIAttributeDefinition(ANSIAttribute.BLINK, ""),
    26: ANSIAttributeDefinition(ANSIAttribute.REVERSE, ""),
    27: ANSIAttributeDefinition(ANSIAttribute.HIDDEN, ""),
    28: ANSIAttributeDefinition(ANSIAttribute.STRIKE, ""),
}


class ANSIColorParser(object):
    """
    Traverse a document, look for ansi_literal_block nodes, parse these
    nodes, and replace them with literal blocks, containing proper child
    nodes for ANSI color sequences.
    """

    def _attribute_from_code(self, code: int) -> ANSIAttributeDefinition | None:
        if code in CODE_ATTRIBUTE_MAP:
            return CODE_ATTRIBUTE_MAP[code]
        elif 20 <= code <= 29:
            return ANSIAttributeDefinition(ANSIAttribute.ITALIC, CODE_COLOR_MAP[code % 10])
        elif 30 <= code <= 37:
            return ANSIAttributeDefinition(ANSIAttribute.FOREGROUND, CODE_COLOR_MAP[code % 10])
        elif 40 <= code <= 47:
            return ANSIAttributeDefinition(ANSIAttribute.BACKGROUND, CODE_COLOR_MAP[code % 10])
        elif 90 <= code <= 97:
            return ANSIAttributeDefinition(ANSIAttribute.FOREGROUND, f"bright_{CODE_COLOR_MAP[code % 10]}")
        elif 100 <= code <= 107:
            return ANSIAttributeDefinition(ANSIAttribute.BACKGROUND, f"bright_{CODE_COLOR_MAP[code % 10]}")
        else:
            return None  # Ignore unknown codes.

    def _create_inline_node(self, text: str, current_attributes: dict[ANSIAttribute, str]):
        if current_attributes:
            classes = list([f"ansi-{attr.to_class_name(value)}" for attr, value in current_attributes.items()])
            return nodes.inline(text=text, classes=classes)
        return nodes.Text(text)

    def _update_attributes(self, code: int, attributes: dict[ANSIAttribute, str]):
        definition = self._attribute_from_code(code)
        if definition is None:
            return
        attributes_to_set = []
        if isinstance(definition.attribute, ANSIAttribute):
            attributes_to_set = [definition.attribute]
        elif isinstance(definition.attribute, list):
            attributes_to_set = definition.attribute
        for attr in attributes_to_set:
            if definition.value:
                attributes[attr] = definition.value
            elif attr in attributes:
                del attributes[attr]

    def _colorize_block_contents(self, block: ansi_literal_block):
        raw = block.rawsource
        literal_node = nodes.literal_block(raw, classes=["ansi-block"])
        block.replace_self(literal_node)

        current_attributes: dict[ANSIAttribute, str] = {}
        last_end = 0
        color_nodes = []
        for match in COLOR_PATTERN.finditer(raw):
            head = raw[last_end : match.start()]
            if head:
                color_nodes.append(self._create_inline_node(head, current_attributes))
            for code in [int(c) for c in match.group(1).split(";")]:
                self._update_attributes(code, current_attributes)
            last_end = match.end()
        tail = raw[last_end:]
        color_nodes.append(self._create_inline_node(tail, current_attributes))
        literal_node.extend(color_nodes)

    def _strip_color_from_block_content(self, block: ansi_literal_block):
        content = COLOR_PATTERN.sub("", block.rawsource)
        literal_node = nodes.literal_block(content, content)
        block.replace_self(literal_node)

    def __call__(self, app, doctree, docname):
        """
        Extract and parse all ansi escapes in ansi_literal_block nodes.
        """
        handler = self._colorize_block_contents
        if app.builder.name != "html":
            handler = self._strip_color_from_block_content
        for ansi_block in doctree.traverse(ansi_literal_block):
            handler(ansi_block)


class ANSIBlockDirective(rst.Directive):
    """
    This directive interprets its content as a literal block with ANSI color
    codes.

    The content is decoded using ``string-escape`` to allow symbolic names
    as \x1b being used instead of the real escape character.
    """

    has_content = True
    option_spec = {
        "escape-char": single_char_or_unicode,
    }

    def run(self):
        text = "\n".join(self.content)
        if "escape-char" in self.options:
            text = text.replace(self.options["escape-char"], "\x1b")
        return [ansi_literal_block(text, text)]


def setup(app):
    app.require_sphinx("8.0")
    app.add_directive("ansi-block", ANSIBlockDirective)
    app.connect("doctree-resolved", ANSIColorParser())
