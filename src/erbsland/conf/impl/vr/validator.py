# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Validation of document trees with per-call traversal and index state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from erbsland.conf.error import ConfValidationError
from erbsland.conf.impl.value_impl import ValueImpl
from erbsland.conf.name import Name
from erbsland.conf.name_path import NamePath
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType
from erbsland.conf.vr.rule import Rule, Constraint
from erbsland.conf.vr.rule_type import RuleType, SECTION_TYPES
from .evaluation import passes, elements
from .model import freeze
from .relationships import KeyDefinition


@dataclass
class Visit:
    """
    Record a selected value/rule pair for the later relationship traversal.

    :var children: Visits in document order, excluding defaults and skipped branches.
    :var indexes: Named indexes built for this particular section instance.
    """

    value: ValueImpl
    rule: Rule
    children: list[Visit] = field(default_factory=list)
    indexes: dict[str, Index] = field(default_factory=dict)


@dataclass
class Index:
    """
    Store index contents for one section instance in one validation call.

    All stored text is normalized using the definition's comparison mode.

    :var values: Component tuples used to enforce composite uniqueness.
    :var whole_values: Comma-separated keys used for complete-key references.
    :var components: Per-component sets used for partial-key references.
    """

    definition: KeyDefinition
    values: set[tuple[str, ...]] = field(default_factory=set)
    whole_values: set[str] = field(default_factory=set)
    components: list[set[str]] = field(default_factory=list)

    def normalized(self, text: str) -> str:
        """Apply the index's case-sensitivity policy to a stored or queried key."""
        return text if self.definition.case_sensitive else text.casefold()

    def contains(self, text: str, component: int | None) -> bool:
        """
        Test membership of a complete key or one component.

        A component index must already have been checked against the definition.
        Query text is normalized with the same policy as stored entries.
        """
        text = self.normalized(text)
        if component is None:
            return text in self.whole_values
        return text in self.components[component]


class Validator:
    """
    Apply a compiled schema using state owned by one validation call.

    The value tree is modified in place. Selected rules and index contents are
    held in a separate visit tree so reusable rules never acquire document state.
    """

    def __init__(self, root: Rule, value: Value, version: int) -> None:
        """
        Prepare validation of a document or a section with regular names.

        :param root: Fully compiled root rule.
        :param value: Root of the selected document subtree.
        :param version: Explicit nonnegative integer used to filter definitions.
        :raises ConfValidationError: If the value or version is unsupported.
        """
        if type(version) is not int or version < 0:
            raise ConfValidationError("The document version must be a nonnegative integer")
        if not isinstance(value, ValueImpl) or value.type not in (
            ValueType.DOCUMENT,
            ValueType.SECTION_WITH_NAMES,
            ValueType.INTERMEDIATE_SECTION,
        ):
            raise ConfValidationError("Validate a document or a section with regular names")
        self.root, self.value, self.version = root, value, version
        self.unexpected: list[ValueImpl] = []

    @staticmethod
    def error(message: str, value: Value, *, name_path: NamePath | None = None) -> None:
        """Raise a validation error at the value's location, optionally overriding its concrete path."""
        raise ConfValidationError(
            message, source=value.location, name_path=name_path if name_path is not None else value.name_path
        )

    def validate(self) -> None:
        """
        Refresh metadata and execute the ordered validation stages.

        Local checks, defaults and uniqueness checks precede unexpected-node
        detection. Key references and dependencies are evaluated only after
        those stages succeed.

        :raises ConfValidationError: On the first failure; partial mutations are retained.
        """
        self.clear(self.value)
        if not self.root._active(self.version):
            self.error("The root rule does not support this document version", self.value)
        visit = self.walk(self.value, self.root)
        if visit is None:
            return
        if self.unexpected:
            self.error("Unexpected value: no active validation rule matches this name", self.unexpected[0])
        self.relationships(visit, {})

    def clear(self, value: ValueImpl) -> None:
        """
        Remove previous defaults and validation metadata within the selected subtree.

        Explicitly supplied values remain in place. Removed default children are
        detached using the value tree's normal removal operation.
        """
        value._validation_rule = None
        value._is_default_value = False
        for child in tuple(value):
            if child.is_default_value:
                value.remove_child(child.name)
            else:
                self.clear(child)

    def local_constraints(self, value: ValueImpl, rule: Rule) -> None:
        """
        Check the type, ordered local constraints and active name constraints.

        Key constraints are deferred until scoped indexes exist. Name checks
        use a temporary text value but report failures at the original node.

        :raises ConfValidationError: On the first type or local-constraint failure.
        """
        if not rule.type.matches(value.type):
            self.error(f"Expected {rule.type.value}, got {value.type.value}", value)
        for constraint in rule.constraints:
            if constraint.kind != "key" and not passes(value, rule, constraint):
                self.constraint_error(value, rule, constraint)
        name_rule = rule._child("name")
        if name_rule is not None and name_rule._active(self.version):
            if not (value.name.is_regular() or value.name.is_text()):
                self.error("Name constraints require a named value", value)
            text = value.name.as_text()
            name_value = ValueImpl(ValueType.TEXT, value.name, text, value.location)
            try:
                self.local_constraints(name_value, name_rule)
            except ConfValidationError as error:
                self.error(error.message, value)

    def constraint_error(self, value: ValueImpl, rule: Rule, constraint: Constraint) -> None:
        """
        Raise a constraint failure using the most specific nonempty custom error.

        Generated messages never include the supplied value. Required bounds
        are included only for nonsecret rules, and node-level custom messages
        provide the fallback when a constraint has no custom message.
        """
        # Diagnostics deliberately describe the constraint, never the supplied value.
        message = constraint.error or rule.custom_error
        if not message:
            message = f"The '{constraint.name}' constraint is not satisfied"
            if not rule.is_secret and constraint.kind in ("minimum", "maximum", "equals", "multiple"):
                message += f" (required: {constraint.value})"
        self.error(message, value)

    def select(self, value: ValueImpl, rule: Rule) -> Rule:
        """
        Validate an ordinary rule or select the first locally matching alternative.

        Alternatives are filtered by version and type, then checked in declaration
        order. Child validation happens later and cannot trigger backtracking.

        :raises ConfValidationError: With the first local failure, or the expected types if none match.
        """
        if rule.type != RuleType.ALTERNATIVES:
            self.local_constraints(value, rule)
            return rule
        active = tuple(child for child in rule.children if child._active(self.version))
        compatible = tuple(child for child in active if child.type.matches(value.type))
        first_error = None
        for candidate in compatible:
            try:
                self.local_constraints(value, candidate)
                return candidate
            except ConfValidationError as error:
                if first_error is None:
                    first_error = error
        if first_error is not None:
            raise first_error
        expected = " or ".join(dict.fromkeys(child.type.value for child in active))
        self.error(f"Expected {expected or 'an active alternative'}, got {value.type.value}", value)

    def walk(self, value: ValueImpl, rule: Rule) -> Visit | None:
        """
        Validate a branch locally, attach metadata, insert defaults and build indexes.

        Children follow document order, with active named rules taking precedence
        over wildcards. Unexpected nodes are recorded for the next stage.
        Scalar list/matrix views preserve the stored type and outer rule metadata.

        :returns: The visit used for relationship checks, or None for an inactive or skipped branch.
        :raises ConfValidationError: If local constraints, required children or uniqueness fail.
        """
        if not rule._active(self.version):
            self.unexpected.append(value)
            return None
        rule = self.select(value, rule)
        if rule.type == RuleType.NOT_VALIDATED:
            return None
        value._validation_rule = rule
        visit = Visit(value, rule)
        if rule.type in (RuleType.VALUE_LIST, RuleType.VALUE_MATRIX):
            entry_rule = rule._child("entry")
            for row in elements(value):
                entries = elements(row) if rule.type == RuleType.VALUE_MATRIX else (row,)
                for child in entries:
                    child_visit = self.walk(child, entry_rule)
                    if child_visit is not None:
                        visit.children.append(child_visit)
            # A scalar used as a one-entry list retains its list-level metadata.
            value._validation_rule = rule
        elif rule.type == RuleType.SECTION_LIST:
            for child in value:
                child_visit = self.walk(child, rule._child("entry"))
                if child_visit is not None:
                    visit.children.append(child_visit)
        elif rule.type in SECTION_TYPES:
            matched = set()
            for child in tuple(value):
                selected = rule._child("named", child.name)
                if selected is None or not selected._active(self.version):
                    selected = rule._child("any")
                if selected is None or not selected._active(self.version):
                    self.unexpected.append(child)
                    continue
                matched.add(selected)
                child_visit = self.walk(child, selected)
                if child_visit is not None:
                    visit.children.append(child_visit)
            for child_rule in rule.children:
                if child_rule._role == "named" and child_rule not in matched and child_rule._active(self.version):
                    self.missing(value, child_rule)
        self.build_indexes(visit)
        return visit

    def missing(self, parent: ValueImpl, rule: Rule) -> None:
        """
        Handle an absent named child using its active alternatives.

        Optional or unvalidated definitions permit absence. Otherwise the first
        active default is copied into the parent, without creating missing parent
        sections or applying ordinary constraints to the default.

        :raises ConfValidationError: If a required child has no applicable default.
        """
        candidates = rule.children if rule.type == RuleType.ALTERNATIVES else (rule,)
        active = tuple(c for c in candidates if c._active(self.version))
        if any(c.type == RuleType.NOT_VALIDATED or c.is_optional for c in active):
            return
        for candidate in active:
            if candidate.has_default:
                if parent.type == ValueType.INTERMEDIATE_SECTION:
                    parent.type = ValueType.SECTION_WITH_NAMES
                parent.add_child(self.default(candidate._default, rule._name, candidate))
                return
        expected = " or ".join(dict.fromkeys(c.type.value for c in active))
        path = NamePath([*parent.name_path, rule._name])
        self.error(f"Missing required {expected} value", parent, name_path=path)

    def default(self, data: Any, name: Name, rule: Rule) -> ValueImpl:
        """
        Create a detached value tree from a default payload checked during compilation.

        Each node receives validation metadata and is marked as a default.
        Mutable time/date-time wrappers are copied to keep documents independent.
        The caller attaches the returned root; ordinary constraints are bypassed.
        """
        if isinstance(data, tuple):
            value = ValueImpl(ValueType.VALUE_LIST, name)
            for index, item in enumerate(data):
                value.add_child(self.default(item, Name.create_index(index), rule._child("entry") or rule))
        else:
            value = ValueImpl.from_data(name, freeze(data))
        value._validation_rule = rule
        value._is_default_value = True
        return value

    def build_indexes(self, visit: Visit) -> None:
        """
        Check uniqueness and build indexes declared by this completed section visit.

        Missing, unvalidated or non-key components contribute empty strings;
        entries with no usable components are omitted. Named indexes are retained
        on the visit for scoped reference checks, while anonymous indexes only
        enforce uniqueness.

        :raises ConfValidationError: At the section-list entry containing a duplicate key.
        """
        for definition in visit.rule._keys:
            index = Index(definition, components=[set() for _ in definition.paths])
            values = visit.value.get(NamePath(list(definition.list_path)))
            if values is not None and values.type == ValueType.SECTION_LIST and values.is_validated:
                for entry in values:
                    parts = []
                    present = False
                    for path in definition.entry_paths:
                        value = entry.get(NamePath(list(path)))
                        if (
                            value is None
                            or not value.is_validated
                            or value.type not in (ValueType.TEXT, ValueType.INTEGER)
                        ):
                            parts.append("")
                        else:
                            present = True
                            parts.append(index.normalized(str(value.native)))
                    if not present:
                        continue
                    key = tuple(parts)
                    if key in index.values:
                        self.error("Duplicate key in section list", entry)
                    index.values.add(key)
                    index.whole_values.add(",".join(key))
                    for component, part in zip(index.components, key):
                        component.add(part)
            if definition.name is not None:
                visit.indexes[definition.name] = index

    def relationships(self, visit: Visit, scope: dict[str, Index]) -> None:
        """
        Validate references and dependencies using indexes for this section instance.

        Local indexes shadow inherited ones in a copied scope. Value and name
        references are checked before descending, and each section's dependencies
        run after its children. Default values are absent from the visit tree.

        :raises ConfValidationError: On the first failed reference or dependency.
        """
        scope = {**scope, **visit.indexes}
        self.key_constraints(visit.value, visit.rule, str(visit.value.native), scope)
        name_rule = visit.rule._child("name")
        if name_rule is not None and name_rule._active(self.version):
            self.key_constraints(visit.value, name_rule, visit.value.name.as_text(), scope)
        for child in visit.children:
            self.relationships(child, scope)
        for dependency in visit.rule._dependencies:

            def configured(paths: tuple[tuple[Name, ...], ...]) -> bool:
                """Return whether any relative path resolves to an explicitly configured value."""
                return any(
                    (value := visit.value.get(NamePath(list(path)))) is not None and not value.is_default_value
                    for path in paths
                )

            if not dependency.mode.accepts(configured(dependency.sources), configured(dependency.targets)):
                self.error(
                    dependency.error or f"The '{dependency.mode.value}' dependency is not satisfied", visit.value
                )

    def key_constraints(self, value: ValueImpl, rule: Rule, text: str, scope: dict[str, Index]) -> None:
        """
        Apply compiled key constraints to a value's text or its name.

        A positive constraint accepts membership in any referenced index or
        component; its negative form requires absence from all of them.

        :param value: Original value used for diagnostics, including name-constraint failures.
        :param text: Scalar representation or name to look up.
        :param scope: Runtime indexes whose references were checked during compilation.
        :raises ConfValidationError: If a key constraint fails.
        """
        for constraint in rule.constraints:
            if constraint.kind != "key":
                continue
            matched = False
            for reference in constraint._prepared:
                index = scope[reference.name]
                matched |= index.contains(text, reference.component)
            if matched == constraint.is_negated:
                self.constraint_error(value, rule, constraint)
