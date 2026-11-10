# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Python keyword builder for reusable validation rules."""

from __future__ import annotations

from copy import deepcopy
from typing import Unpack

from erbsland.conf.error import ConfValidationError
from erbsland.conf.name import Name
from erbsland.conf.impl.vr.model import Node, PathLike, freeze, path_parts, regular_name
from .dependency_mode import DependencyMode
from .options import RuleOptions
from .rule_type import RuleType, TypeLike, SECTION_TYPES
from .rules import Rules


class RulesBuilder:
    """Build a schema with native values and ordered keyword constraints.

    Declare parent rules before their children. Returned branch views share this
    builder. Only the original builder can build or reset; reset invalidates old
    branch views. Building leaves the builder available for further editing.
    """

    def __init__(self) -> None:
        self._root = Node(role="root", type=RuleType.SECTION)
        self._node = self._root
        self._owner = self

    def _check(self) -> None:
        if self._root is not self._owner._root:
            raise ConfValidationError("This branch belongs to a reset builder")

    def _view(self, node: Node) -> RulesBuilder:
        view = object.__new__(RulesBuilder)
        view._root, view._node, view._owner = self._root, node, self._owner
        return view

    @staticmethod
    def _apply(node: Node, options: RuleOptions) -> None:
        options = dict(options)
        entry_type = options.pop("entry_type", None)
        entry_options = options.pop("entry_options", None)
        if entry_options is not None and entry_type is None:
            raise ConfValidationError("'entry_options' requires 'entry_type' in the same declaration")
        if entry_type is not None:
            type_ = RuleType.from_type(entry_type)
            if node.type != RuleType.VALUE_LIST or not type_.is_scalar() or node.child("entry") is not None:
                raise ConfValidationError("'entry_type' requires a value list without an existing entry rule")
            entry = Node(name=regular_name("vr_entry"), role="entry", type=type_)
            if entry_options is not None and not isinstance(entry_options, dict):
                raise ConfValidationError("'entry_options' must be a mapping of rule options")
            RulesBuilder._apply(entry, entry_options or {})
            node.children.append(entry)
        for key, value in options.items():
            if not isinstance(key, str):
                raise ConfValidationError("Rule option names must be strings")
            name = "in" if key == "in_" else key
            node.options[name] = freeze(value)

    def _parent(self, path: PathLike) -> tuple[Node, Name]:
        self._check()
        parts = path_parts(path)
        parent = self._node
        for name in parts[:-1]:
            parent = parent.child("named", name)
            if parent is None or parent.type not in SECTION_TYPES:
                raise ConfValidationError("Declare parent sections before adding child rules")
        return parent, parts[-1]

    def _add(
        self, parent: Node, name: Name, role: str, type_: TypeLike, options: RuleOptions, alternative: bool
    ) -> RulesBuilder:
        self._check()
        resolved = RuleType.from_type(type_)
        if resolved == RuleType.ALTERNATIVES:
            raise ConfValidationError("Use add_alternative() to declare alternatives")
        new = Node(name=name, role=role, type=resolved, spelling=name)
        self._apply(new, options)
        existing = parent.child(role, name)
        if not alternative:
            if existing is not None:
                raise ConfValidationError("A rule with this name or role already exists")
            parent.children.append(new)
        else:
            if existing is None:
                existing = Node(name=name, role=role, type=RuleType.ALTERNATIVES, spelling=name)
                parent.children.append(existing)
            if existing.type != RuleType.ALTERNATIVES:
                raise ConfValidationError("An ordinary rule cannot be extended with alternatives")
            new.role = "alternative"
            existing.children.append(new)
        return self._view(new)

    def add_rule(self, path: PathLike, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Declare a literal named rule and return its branch view."""
        parent, name = self._parent(path)
        return self._add(parent, name, "named", type_, options, False)

    def add_alternative(self, path: PathLike, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Append an alternative and return a view for that alternative's children."""
        parent, name = self._parent(path)
        return self._add(parent, name, "named", type_, options, True)

    def add_entry(self, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Declare the entry rule of this list."""
        return self._add(self._node, regular_name("vr_entry"), "entry", type_, options, False)

    def add_entry_alternative(self, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Append an alternative entry definition for this list."""
        return self._add(self._node, regular_name("vr_entry"), "entry", type_, options, True)

    def add_any(self, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Declare a wildcard for otherwise unmatched child names."""
        return self._add(self._node, regular_name("vr_any"), "any", type_, options, False)

    def add_any_alternative(self, type_: TypeLike, **options: Unpack[RuleOptions]) -> RulesBuilder:
        """Append an alternative for otherwise unmatched child names."""
        return self._add(self._node, regular_name("vr_any"), "any", type_, options, True)

    def configure_name(self, **options: Unpack[RuleOptions]) -> None:
        """Configure text constraints on this named rule or wildcard's names."""
        self._check()
        name_rule = self._node.child("name")
        if name_rule is None:
            name_rule = Node(name=regular_name("vr_name"), role="name", type=RuleType.TEXT)
            self._apply(name_rule, options)
            self._node.children.append(name_rule)
        else:
            self._apply(name_rule, options)

    def branch(self, path: PathLike) -> RulesBuilder:
        """Return a view of an existing literal named rule."""
        parent, name = self._parent(path)
        node = parent.child("named", name)
        if node is None or node.type == RuleType.ALTERNATIVES:
            raise ConfValidationError("Branch must select an existing non-alternative rule")
        return self._view(node)

    def configure_root(self, **options: Unpack[RuleOptions]) -> None:
        """Configure this view's root rule, preserving existing children."""
        self._check()
        temporary = deepcopy(self._node)
        self._apply(temporary, options)
        self._node.options = temporary.options
        # Preserve existing branch identities.
        self._node.children.extend(temporary.children[len(self._node.children) :])

    def add_key(self, *paths: PathLike, name: str | None = None, case_sensitive: bool = False) -> None:
        """Declare a scoped unique index; multiple paths form a composite key."""
        self._check()
        record = {"key": tuple(str_path(p) for p in paths), "case_sensitive": case_sensitive}
        if name is not None:
            record["name"] = name
        self._node.keys.append(record)

    def add_dependency(
        self,
        mode: DependencyMode | str,
        *,
        source: PathLike | list[PathLike] | tuple[PathLike, ...],
        target: PathLike | list[PathLike] | tuple[PathLike, ...],
        error: str = "",
    ) -> None:
        """Require a relationship between explicitly configured relative paths."""
        self._check()

        def paths(values: PathLike | list[PathLike] | tuple[PathLike, ...]) -> tuple[str, ...]:
            values = values if isinstance(values, (tuple, list)) else (values,)
            return tuple(str_path(p) for p in values)

        self._node.dependencies.append({"mode": mode, "source": paths(source), "target": paths(target), "error": error})

    def build(self) -> Rules:
        """Validate and return an independent immutable rules snapshot."""
        self._check()
        if self is not self._owner:
            raise ConfValidationError("Build rules through the original builder")
        from erbsland.conf.impl.vr.compiler import compile_rules

        return Rules(compile_rules(deepcopy(self._root)))

    def reset(self) -> None:
        """Clear the original builder and invalidate previously returned branches."""
        self._check()
        if self is not self._owner:
            raise ConfValidationError("Reset rules through the original builder")
        self._root = self._node = Node(role="root", type=RuleType.SECTION)


def str_path(path: PathLike) -> str:
    """Detach a caller-owned NamePath before storing it in the builder."""
    from erbsland.conf.name_path import NamePath

    return str(NamePath(list(path_parts(path))))
