# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Validate definitions and freeze the reusable rule tree."""

from __future__ import annotations

from typing import Any

from erbsland.conf.name import Name
from erbsland.conf.vr.rule import Rule
from erbsland.conf.vr.rule_type import RuleType, LIST_TYPES, SECTION_TYPES
from .constraints import compile_options, scalar_matches
from .model import Node, fail, freeze
from .relationships import finalize_relationships


def default_matches(type_: RuleType, value: Any) -> bool:
    """
    Check whether a frozen default has the declared scalar or collection shape.

    Lists and matrices also accept a single scalar. Only the default's type
    and shape are checked here; entry constraints and ordinary value constraints
    do not apply to defaults.
    """
    if type_ == RuleType.VALUE_LIST:
        return (
            all(scalar_matches(RuleType.VALUE, v) for v in value)
            if isinstance(value, tuple)
            else scalar_matches(RuleType.VALUE, value)
        )
    if type_ == RuleType.VALUE_MATRIX:
        return (
            all(default_matches(RuleType.VALUE_LIST, v) for v in value)
            if isinstance(value, tuple)
            else scalar_matches(RuleType.VALUE, value)
        )
    return type_.is_scalar() and scalar_matches(type_, value)


def compile_node(
    node: Node,
    path: tuple[Name, ...] = (),
    definition: tuple[Name, ...] = (),
    parent: Node | None = None,
    parent_role: str | None = None,
) -> Rule:
    """
    Check one definition and recursively create its immutable rule tree.

    Structural roles remain separate from target names so literal names such as
    ``vr_entry`` can coexist with list-entry definitions. Relationship records
    retain their source locations but receive paths at their insertion point,
    including when they originate in a template.

    :param node: Mutable definition after template expansion.
    :param path: Decoded symbolic value path used by public rule metadata.
    :param definition: Declaration path used for schema diagnostics.
    :param parent: Enclosing definition, used to check structural placement.
    :param parent_role: Effective parent role, inherited through alternatives.
    :returns: A rule tree whose relationship records still need finalization.
    :raises ConfValidationError: If types, options, defaults or child placement are invalid.
    """
    if node.type is None:
        fail("A rule must have either 'type' or 'use_template'", node, definition)
    if node.role == "name" and (node.type != RuleType.TEXT or node.children):
        fail("'vr_name' must be a text rule without subsections", node, definition)
    effective_role = parent_role if node.role == "alternative" else node.role
    if node.role == "name" and parent_role not in ("named", "any"):
        fail("'vr_name' requires a named or wildcard parent", node, definition)
    if node.role == "entry" and (parent is None or parent.type not in LIST_TYPES):
        fail("'vr_entry' requires a list parent", node, definition)
    if node.role == "any" and (parent is None or parent.type not in SECTION_TYPES):
        fail("'vr_any' requires a section parent", node, definition)
    constraints, versions = compile_options(node, definition)
    default = freeze(node.options.get("default"))
    has_default = "default" in node.options
    optional = node.options.get("is_optional", False)
    if has_default and optional:
        fail("A rule cannot combine a default with optionality", node, definition)
    if has_default and not default_matches(node.type, default):
        fail("The default must match a scalar, value-list or matrix rule type", node, definition, "default")
    if effective_role in ("entry", "any", "name") and (has_default or optional):
        fail("Entry, wildcard and name rules cannot have defaults or optionality", node, definition)
    if node.options.get("is_secret", False) and not node.type.is_scalar():
        fail("Only scalar rules can be secret", node, definition)
    if node.type == RuleType.NOT_VALIDATED:
        if constraints or node.children or node.keys or node.dependencies or has_default:
            fail("'NotValidated' cannot have constraints, defaults or child rules", node, definition)
    if node.type in LIST_TYPES and node.child("entry") is None:
        fail("A list rule requires a 'vr_entry' rule", node, definition)
    if node.type in LIST_TYPES and any(child.role != "entry" for child in node.children):
        fail("Only 'vr_entry' is allowed inside a list rule", node, definition)
    if node.type.is_scalar() and any(child.role != "name" for child in node.children):
        fail("Scalar rules cannot have child rules", node, definition)
    if node.type == RuleType.ALTERNATIVES:
        if node.options or not node.children:
            fail("An alternatives container must contain definitions and no attributes", node, definition)
        if sum("default" in child.options for child in node.children) > 1:
            fail("Only one alternative may define a default", node, definition)
        if any(child.options.get("is_optional", False) for child in node.children[1:]):
            fail("Only the first alternative may be optional", node, definition)
        if any("default" in child.options for child in node.children) and any(
            child.options.get("is_optional", False) for child in node.children
        ):
            fail("Alternatives cannot combine defaults and optionality", node, definition)
    children = []
    targets = set()
    for index, child in enumerate(node.children):
        if node.type == RuleType.ALTERNATIVES:
            child_path = path
            child_definition = (*definition, Name.create_index(index))
        else:
            target = (child.role, child.name if child.role == "named" else None)
            if target in targets:
                fail("Duplicate decoded target name", child, (*definition, child.spelling or child.name))
            targets.add(target)
            child_path = (*path, child.name)
            child_definition = (*definition, child.spelling or child.name)
        # Entry alternatives must meet the same requirements as an ordinary entry.
        entry_parent = parent if node.role == "entry" and node.type == RuleType.ALTERNATIVES else node
        if child.role == "entry" or node.role == "entry" and child.role == "alternative":
            list_type = node.type if child.role == "entry" else entry_parent.type
            accepted = SECTION_TYPES if list_type == RuleType.SECTION_LIST else {t for t in RuleType if t.is_scalar()}
            if child.type != RuleType.ALTERNATIVES and child.type not in accepted:
                fail("Entry rule type is incompatible with its list", child, child_definition)
        children.append(compile_node(child, child_path, child_definition, node, effective_role))
    return Rule(
        type=node.type,
        _path=path,
        _definition_path=definition,
        _role=node.role,
        _name=node.name,
        title=node.options.get("title", ""),
        description=node.options.get("description", ""),
        custom_error=node.options.get("error", ""),
        is_optional=optional,
        is_secret=node.options.get("is_secret", False),
        case_sensitive=node.options.get("case_sensitive", False),
        has_default=has_default,
        _default=default,
        constraints=constraints,
        children=tuple(children),
        location=node.location,
        _versions=versions,
        _keys=tuple(
            tuple(
                {
                    **record,
                    "_definition_path": (*definition, Name.create_regular("vr_key"), Name.create_index(i)),
                }.items()
            )
            for i, record in enumerate(node.keys)
        ),
        _dependencies=tuple(
            tuple(
                {
                    **record,
                    "_definition_path": (*definition, Name.create_regular("vr_dependency"), Name.create_index(i)),
                }.items()
            )
            for i, record in enumerate(node.dependencies)
        ),
    )


def compile_rules(node: Node) -> Rule:
    """
    Compile and finalize a complete root definition for repeated validation.

    Local definition checks precede relationship resolution, so every index and
    dependency is checked against the complete compiled tree.

    :returns: The immutable root rule, including resolved relationship definitions.
    :raises ConfValidationError: If any definition or relationship is invalid.
    """
    return finalize_relationships(compile_node(node))
