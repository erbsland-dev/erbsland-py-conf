#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from dataclasses import dataclass

from erbsland.conf.test_output import TestOutput
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType
from erbsland.conf.source import SourceIdentifier


@dataclass(slots=True)
class StackFrame:
    value: Value
    indent: str
    is_last: bool


class ValueTreeHelper:
    """Helper class to render graphical value trees."""

    def __init__(self, root_value: Value, output_format: TestOutput = TestOutput.DEFAULT):
        if not isinstance(root_value, Value):
            raise TypeError(f"root_value must be a Value")
        self._root_value = root_value
        self._output_format = output_format
        self._show_sid: bool = bool(output_format & TestOutput.SOURCE_ID)
        self._show_pos: bool = bool(output_format & TestOutput.POSITION)
        self._align: bool = bool(output_format & TestOutput.ALIGN_VALUES)
        self._lines: list[str] = []
        # Collect entries as (tree_part, value_text, pos_text)
        self._entries: list[tuple[str, str, str]] = []
        self._label_index: int = 0
        self._label_map: dict[SourceIdentifier, str] = {}
        self._label_list: list[tuple[str, SourceIdentifier]] = []

    def render(self) -> list[str]:
        """Render and return the lines of the value tree."""
        stack: list[StackFrame] = [StackFrame(self._root_value, "", True)]

        while stack:
            frame = stack.pop()
            value = frame.value
            indent = frame.indent
            is_last = frame.is_last
            name = self._compute_name(value)
            pos_text = self._compute_position(value)
            self._emit_line(value, name, pos_text, indent, is_last)
            self._push_children(stack, value, indent, is_last)

        # Assemble lines (with optional alignment)
        if self._entries:
            if self._align:
                max_len = max(len(tree) for tree, _, _ in self._entries)
            else:
                max_len = -1  # indicates no alignment
            for tree, val_text, pos in self._entries:
                if max_len >= 0:
                    pad = " " * (max_len - len(tree) + 1)
                    line = f"{tree}{pad}=> {val_text}{pos}"
                else:
                    line = f"{tree} => {val_text}{pos}"
                self._lines.append(line)

        if self._show_sid:
            self._append_source_labels()

        return self._lines

    @staticmethod
    def _compute_name(value: Value) -> str:
        if value.is_root or value.type == ValueType.DOCUMENT:
            return "<Document>"
        name_path = value.name_path
        if len(name_path) == 0:
            return "<Empty>"
        last = name_path[-1]
        return last.to_path_text()

    def _compute_position(self, value: Value) -> str:
        if not (self._show_sid or self._show_pos):
            return ""
        parts: list[str] = ["["]
        if self._show_sid:
            parts.append(self._append_source_identifier(value))
        if self._show_pos:
            loc = value.location
            if loc is None:
                parts.append("undefined")
            else:
                parts.append(str(loc.position))
        parts.append("]")
        return "".join(parts)

    def _append_source_identifier(self, value: Value) -> str:
        loc = value.location
        sid = loc.source_identifier if loc is not None else None
        if sid is None:
            return "no source:"
        label = self._label_map.get(sid)
        if label is not None:
            return label + ":"
        labels = "ABCDEFGHIJKLMNPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz+"
        idx = min(self._label_index, len(labels) - 1)
        label = labels[idx]
        if self._label_index < len(labels) - 2:
            self._label_index += 1
        self._label_map[sid] = label
        self._label_list.append((label, sid))
        return label + ":"

    def _append_source_labels(self) -> None:
        for label, sid in self._label_list:
            self._lines.append(f"{label}: {sid}")

    def _emit_line(self, value: Value, name: str, pos: str, indent: str, is_last: bool) -> None:
        if value is self._root_value:
            tree = f"{name}"
        else:
            branch = "└───" if is_last else "├───"
            tree = f"{indent}{branch}{name}"
        val_text = value.to_test_text(self._output_format)
        self._entries.append((tree, val_text, pos))

    def _push_children(
        self,
        stack: list[StackFrame],
        value: Value,
        indent: str,
        is_last_parent: bool,
    ) -> None:
        children = list(iter(value))

        count = len(children)
        for i in range(count - 1, -1, -1):
            child = children[i]
            last = i == count - 1
            child_indent = indent
            if value is not self._root_value:
                child_indent += "    " if is_last_parent else "│   "
            stack.append(StackFrame(child, child_indent, last))
