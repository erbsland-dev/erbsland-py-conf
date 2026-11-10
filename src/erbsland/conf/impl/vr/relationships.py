# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Compile scoped indexes and dependencies against literal configuration paths."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from erbsland.conf.error import ConfValidationError
from erbsland.conf.location import Location
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.vr.dependency_mode import DependencyMode
from erbsland.conf.vr.rule import Rule
from erbsland.conf.vr.rule_type import RuleType, SECTION_TYPES
from .constraints import sequence
from .model import path_parts, regular_name


@dataclass(frozen=True, slots=True)
class KeyDefinition:
    """
    An immutable index definition resolved against the compiled schema.

    :var name: Normalized index name, or None for uniqueness checking only.
    :var paths: Original symbolic key paths relative to the declaring section.
    :var list_path: Path from that section to the shared section list.
    :var entry_paths: Paths from each list entry to the indexed components.
    :var case_sensitive: Comparison mode for uniqueness and key references.
    :var location: Source location of the index declaration, when available.
    :var types: Supported text/integer types for each component across alternatives.
    """

    name: str | None
    paths: tuple[tuple[Name, ...], ...]
    list_path: tuple[Name, ...]
    entry_paths: tuple[tuple[Name, ...], ...]
    case_sensitive: bool
    location: Location | None
    types: tuple[frozenset[RuleType], ...]


@dataclass(frozen=True, slots=True)
class Dependency:
    """
    A checked relationship between paths relative to its declaring section.

    :var mode: Boolean operation applied to source and target presence.
    :var sources: Paths whose explicitly configured presence is combined with OR.
    :var targets: Target paths combined with the same presence semantics.
    :var error: Optional custom failure message; an empty message uses the default.
    :var location: Source location of the dependency declaration, when available.
    """

    mode: DependencyMode
    sources: tuple[tuple[Name, ...], ...]
    targets: tuple[tuple[Name, ...], ...]
    error: str
    location: Location | None


@dataclass(frozen=True, slots=True)
class KeyReference:
    """
    A reference to a scoped index or one component of a composite index.

    :var name: Normalized index name.
    :var component: Zero-based component index, or None to match the complete key.
    """

    name: str
    component: int | None = None


def key_reference(text: str) -> KeyReference:
    """
    Parse an index name with an optional component index, such as ``users[0]``.

    Scope lookup and component bounds are checked later, once all index
    definitions are available.

    :raises ConfValidationError: If the reference has an invalid path shape.
    """
    parts = path_parts(text, indexes=True)
    if not parts[0].is_regular() or len(parts) > 2 or len(parts) == 2 and not parts[1].is_index():
        raise ConfValidationError("A key reference must be an index name with an optional component index")
    return KeyReference(parts[0].as_text(), parts[1].as_index() if len(parts) == 2 else None)


def alternatives(rule: Rule) -> tuple[Rule, ...]:
    """Return an alternatives container's candidates, or the rule itself as one candidate."""
    return rule.children if rule.type == RuleType.ALTERNATIVES else (rule,)


def resolve_key(root: Rule, path: tuple[Name, ...]) -> tuple[tuple[Name, ...], tuple[Name, ...], frozenset[RuleType]]:
    """
    Resolve a key field through exactly one section list in the schema.

    Path components are literal configuration names. Only immediately after a
    section-list rule does ``vr_entry`` denote the structural entry rule.
    Alternatives are followed to collect the possible indexed scalar types.

    :param root: Rule of the section declaring the index.
    :param path: Symbolic path relative to that section.
    :returns: The list path, the path within an entry, and its supported key types.
    :raises ConfValidationError: If the path cannot select a text or integer field in one list.
    """
    current = (root,)
    split = None
    for index, name in enumerate(path):
        following = []
        for rule in current:
            for candidate in alternatives(rule):
                if candidate.type == RuleType.SECTION_LIST:
                    if name.as_text() != "vr_entry" or split is not None:
                        raise ConfValidationError("Key paths must cross exactly one section list using 'vr_entry'")
                    child = candidate._child("entry")
                else:
                    child = candidate._child("named", name)
                if child is not None:
                    following.append(child)
        if not following:
            raise ConfValidationError("Key path does not resolve to a declared rule")
        if any(c.type == RuleType.SECTION_LIST for r in current for c in alternatives(r)):
            split = index
        current = tuple(following)
    if split is None or split == 0 or split == len(path) - 1:
        raise ConfValidationError("A key must select a value inside a section-list entry")
    if not any(c.type in (RuleType.TEXT, RuleType.INTEGER) for r in current for c in alternatives(r)):
        raise ConfValidationError("Key fields must have a text or integer rule")
    types = frozenset(c.type for r in current for c in alternatives(r) if c.type in (RuleType.TEXT, RuleType.INTEGER))
    return path[:split], path[split + 1 :], types


def resolve_dependency(root: Rule, path: tuple[Name, ...]) -> None:
    """
    Check that a dependency path selects a conditionally present node.

    Optionality or a default on any selected path component makes the target
    conditional. The declaring section's own optionality does not count.
    Paths may end at alternatives but cannot traverse alternatives or lists.

    :raises ConfValidationError: If the path is unresolved, unsupported or always required.
    """
    current = root
    conditional = False
    for name in path:
        if current.type not in SECTION_TYPES:
            raise ConfValidationError("Dependency paths cannot cross lists or alternatives")
        current = current._child("named", name)
        if current is None:
            raise ConfValidationError("Dependency path does not resolve to a declared rule")
        conditional |= any(r.is_optional or r.has_default for r in alternatives(current))
    if not conditional:
        raise ConfValidationError("Dependency paths must reference conditionally present nodes")


def compile_key(record: dict[str, Any], rule: Rule) -> KeyDefinition:
    """
    Compile one index record and resolve all its component paths.

    Composite components must address the same section list. A missing name
    creates an anonymous uniqueness check; named indexes are added to scope by
    ``finalize_relationships``.

    :param record: Raw index attributes, optionally carrying source metadata.
    :param rule: Section rule that declares the index.
    :raises ConfValidationError: If attributes, paths or comparison options are invalid.
    """
    unknown = set(record) - {"key", "name", "case_sensitive", "_location", "_definition_path"}
    if unknown or "key" not in record:
        raise ConfValidationError("An index requires 'key' and supports only 'name' and 'case_sensitive'")
    paths = tuple(path_parts(v) for v in sequence(record["key"]))
    if not paths or len(set(paths)) != len(paths):
        raise ConfValidationError("Index paths must be nonempty and unique")
    resolved = [resolve_key(rule, path) for path in paths]
    list_path = resolved[0][0]
    if any(p[0] != list_path for p in resolved):
        raise ConfValidationError("Composite keys must refer to the same section list")
    name = record.get("name")
    if name is not None:
        if type(name) is not str:
            raise ConfValidationError("An index name must be text")
        name = regular_name(name).as_text()
    sensitive = record.get("case_sensitive", False)
    if type(sensitive) is not bool:
        raise ConfValidationError("Index 'case_sensitive' must be boolean")
    return KeyDefinition(
        name,
        paths,
        list_path,
        tuple(p[1] for p in resolved),
        sensitive,
        record.get("_location"),
        tuple(p[2] for p in resolved),
    )


def compile_dependency(record: dict[str, Any], rule: Rule) -> Dependency:
    """
    Compile one dependency record and check every relative source and target path.

    :param record: Raw dependency attributes, optionally carrying source metadata.
    :param rule: Section rule against which paths are resolved.
    :returns: A dependency ready for presence checks during document validation.
    :raises ConfValidationError: If its mode, attributes or referenced paths are invalid.
    """
    if set(record) - {"mode", "source", "target", "error", "_location", "_definition_path"} or not {
        "mode",
        "source",
        "target",
    } <= set(record):
        raise ConfValidationError("Dependencies require 'mode', 'source', 'target' and allow an optional 'error'")
    mode = DependencyMode.from_text(record["mode"])
    sources = tuple(path_parts(v) for v in sequence(record["source"]))
    targets = tuple(path_parts(v) for v in sequence(record["target"]))
    if not sources or not targets:
        raise ConfValidationError("Dependency source and target lists must not be empty")
    for path in (*sources, *targets):
        resolve_dependency(rule, path)
    error = record.get("error", "")
    if type(error) is not str:
        raise ConfValidationError("Dependency error must be text")
    return Dependency(mode, sources, targets, error, record.get("_location"))


def finalize_relationships(rule: Rule, scope: dict[str, KeyDefinition] | None = None) -> Rule:
    """
    Resolve relationship records and key references throughout an immutable tree.

    Local named indexes shadow inherited names, while duplicate names in one
    section are rejected. Each child receives its own scope copy, preventing
    sibling definitions from leaking into one another. Errors use declaration
    paths, including escaped names and template insertion points.

    :param rule: Compiled rule whose relationship records have not been finalized.
    :param scope: Named index definitions inherited from enclosing sections.
    :returns: A replacement rule tree with checked relationships; inputs are unchanged.
    :raises ConfValidationError: If a relationship or key reference is invalid.
    """
    scope = dict(scope or {})
    if (rule._keys or rule._dependencies) and rule.type not in SECTION_TYPES:
        raise ConfValidationError(
            "Indexes and dependencies require a section rule",
            source=rule.location,
            name_path=NamePath(list(rule._definition_path)),
        )
    keys = []
    dependencies = []
    local_names = set()
    for records, output, compiler in (
        (rule._keys, keys, compile_key),
        (rule._dependencies, dependencies, compile_dependency),
    ):
        for record in records:
            try:
                item = compiler(dict(record), rule)
                output.append(item)
                if isinstance(item, KeyDefinition) and item.name is not None:
                    if item.name in local_names:
                        raise ConfValidationError("Duplicate index name in the same scope")
                    local_names.add(item.name)
                    scope[item.name] = item
            except ConfValidationError as error:
                data = dict(record)
                raise ConfValidationError(
                    error.message,
                    source=data.get("_location", rule.location),
                    name_path=NamePath(list(data.get("_definition_path", rule._definition_path))),
                ) from None
    for constraint in rule.constraints:
        if constraint.kind == "key":
            definition_path = NamePath([*rule._definition_path, Name.create_regular(constraint.name)])
            seen = set()
            for reference in constraint._prepared:
                if reference in seen:
                    raise ConfValidationError(
                        "Key references must be unique", source=constraint.location, name_path=definition_path
                    )
                seen.add(reference)
                if reference.name not in scope:
                    raise ConfValidationError(
                        "Unknown or out-of-scope key index",
                        source=constraint.location or rule.location,
                        name_path=definition_path,
                    )
                if reference.component is not None and reference.component >= len(scope[reference.name].paths):
                    raise ConfValidationError(
                        "Key component index is out of range",
                        source=constraint.location or rule.location,
                        name_path=definition_path,
                    )
                index = scope[reference.name]
                expected = (
                    frozenset({RuleType.TEXT})
                    if len(index.paths) > 1 and reference.component is None
                    else index.types[reference.component or 0]
                )
                if rule.type not in expected:
                    raise ConfValidationError(
                        "Key reference type must match the indexed field",
                        source=constraint.location or rule.location,
                        name_path=definition_path,
                    )
    children = tuple(finalize_relationships(child, scope) for child in rule.children)
    return replace(rule, children=children, _keys=tuple(keys), _dependencies=tuple(dependencies))
