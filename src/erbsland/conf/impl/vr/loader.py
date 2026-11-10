# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""Load rule definitions from an ordinary parsed ELCL document."""

from __future__ import annotations

from copy import deepcopy

from erbsland.conf.document import Document
from erbsland.conf.error import ConfValidationError
from erbsland.conf.name import Name
from erbsland.conf.value import Value
from erbsland.conf.value_type import ValueType
from erbsland.conf.vr.rule_type import RuleType
from .model import Node, native, regular_name

CONTROLS = {"vr_entry": "entry", "vr_any": "any", "vr_name": "name"}


def declaration(name: str) -> tuple[str, str]:
    """
    Decode one declaration component and determine its structural role.

    The input is an already normalized ELCL name. Exactly one ``vr_literal_``
    or legacy ``vr_vr_`` prefix is decoded; the result is always a literal
    named target, even when it resembles another escape or control name.

    :returns: The decoded target name and its role, such as ``named`` or ``entry``.
    :raises ConfValidationError: If a decoded name is invalid or a reserved name is misplaced.
    """
    if name.startswith("vr_literal_"):
        return regular_name(name[len("vr_literal_") :]).as_text(), "named"
    if name.startswith("vr_vr_"):
        return regular_name(name[3:]).as_text(), "named"
    if name in CONTROLS:
        return name, CONTROLS[name]
    if name.startswith("vr_"):
        raise ConfValidationError("Unknown or misplaced reserved name")
    return name, "named"


class Loader:
    """
    Translate parsed ELCL into mutable definitions without changing the source.

    Templates are read only when referenced. Expansion preserves original source
    locations; the compiler later assigns declaration paths at the use site.
    """

    def __init__(self, document: Document) -> None:
        """Retain the source document and initialize the template lookup for loading."""
        self.document = document
        self.templates: dict[str, Value] = {}

    def load(self) -> Node:
        """
        Load the root definitions and expand templates where they are used.

        :returns: A section root ready for structural and relationship compilation.
        :raises ConfValidationError: If the source is not a document or contains invalid rule syntax.
        """
        if not isinstance(self.document, Document):
            raise ConfValidationError("Rules.from_document() requires a Document")
        root = Node(role="root", type=RuleType.SECTION, location=self.document.location)
        templates = self.document.get("vr_template")
        if templates is not None:
            if templates.type not in (ValueType.SECTION_WITH_NAMES, ValueType.INTERMEDIATE_SECTION):
                self.error("Templates must be a root section with regular names", templates)
            self.templates = {child.name.as_text(): child for child in templates if child.name.is_regular()}
        self.children(self.document, root, False, root=True)
        return root

    @staticmethod
    def error(message: str, value: Value) -> None:
        """Raise a definition error at the source value's location and declaration path."""
        raise ConfValidationError(message, source=value.location, name_path=value.name_path)

    def children(self, source: Value, node: Node, in_template: bool, *, root: bool = False) -> None:
        """
        Append child definitions and relationship records in source order.

        Children with an inherited declaration spelling are merged as template
        overrides. Distinct spellings stay separate so compilation can detect
        collisions after literal-name decoding.

        :param source: Parsed section whose children are being loaded.
        :param node: Mutable destination, possibly already populated by a template.
        :param in_template: Whether nested template references must be rejected.
        :param root: Whether to skip the template registry and reject root attributes.
        :raises ConfValidationError: If child names, structural sections or overrides are invalid.
        """
        for value in source:
            if not value.name.is_regular():
                self.error("Text names are not allowed in validation rules", value)
            name = value.name.as_text()
            if root and name == "vr_template":
                continue
            if name in ("vr_key", "vr_dependency"):
                if value.type != ValueType.SECTION_LIST:
                    self.error(f"'{name}' must be a section list", value)
                records = node.keys if name == "vr_key" else node.dependencies
                for entry in value:
                    record = {}
                    for field in entry:
                        if not field.name.is_regular():
                            self.error("Relationship attributes must have regular names", field)
                        record[field.name.as_text()] = native(field)
                    record["_location"] = entry.location
                    record["_definition_path"] = tuple(entry.name_path)
                    records.append(record)
            elif value.type.is_map() or value.type == ValueType.SECTION_LIST:
                try:
                    decoded, role = declaration(name)
                    child = self.read(value, regular_name(decoded), role, in_template)
                    existing = next((c for c in node.children if c.spelling == child.spelling), None)
                    if existing is None:
                        node.children.append(child)
                    else:
                        self.merge(existing, child, value)
                except ConfValidationError as error:
                    if error.location is not None:
                        raise
                    self.error(error.message, value)
            elif root:
                self.error("Root rule attributes require the Python builder", value)

    def read(self, value: Value, name: Name, role: str, in_template: bool) -> Node:
        """
        Read one rule or alternatives container, applying any template overrides.

        Implicit ancestor sections receive a section type. A local child override
        may leave its type unset until it is merged with an inherited definition.
        Alternative templates are copied as a whole and cannot be customized.

        :param value: Parsed declaration or alternative entry.
        :param name: Decoded symbolic target name.
        :param role: Structural role assigned independently of the target name.
        :param in_template: Whether this declaration belongs to an expanded template.
        :returns: A mutable definition with ordered options and retained source locations.
        :raises ConfValidationError: If types, template usage or declaration syntax are invalid.
        """
        if value.type == ValueType.SECTION_WITH_TEXTS:
            self.error("Text names are not allowed in validation rules", value)
        node = Node(name=name, role=role, spelling=value.name, location=value.location)
        if value.type == ValueType.SECTION_LIST:
            node.type = RuleType.ALTERNATIVES
            for entry in value:
                alternative = self.read(entry, name, "alternative", in_template)
                node.children.append(alternative)
            return node
        attributes = {
            child.name.as_text(): child
            for child in value
            if child.name.is_regular() and not child.type.is_map() and child.type != ValueType.SECTION_LIST
        }
        if "type" in attributes and "use_template" in attributes:
            self.error("A rule cannot define both 'type' and 'use_template'", value)
        if "use_template" in attributes:
            if in_template:
                self.error("Templates cannot reference other templates", attributes["use_template"])
            template_name = native(attributes["use_template"])
            if type(template_name) is not str:
                self.error("'use_template' must be text", attributes["use_template"])
            key = regular_name(template_name).as_text()
            if key not in self.templates:
                self.error("Unknown template", attributes["use_template"])
            template = self.templates[key]
            node = self.read(template, name, role, True)
            node.spelling = value.name
            if node.type == RuleType.ALTERNATIVES:
                if len(value) != 1 or role == "name":
                    self.error("Alternative templates cannot be customized or used for names", value)
                return node
        elif "type" in attributes:
            if attributes["type"].type != ValueType.TEXT:
                self.error("'type' must be text", attributes["type"])
            try:
                node.type = RuleType.from_type(native(attributes["type"]))
            except ConfValidationError as error:
                self.error(error.message, attributes["type"])
            if node.type == RuleType.ALTERNATIVES:
                self.error("Alternatives must be declared as a section list", attributes["type"])
        elif role == "name":
            node.type = RuleType.TEXT
        elif value.type == ValueType.INTERMEDIATE_SECTION:
            node.type = RuleType.SECTION
        elif not in_template:
            # Local child overrides may inherit the type from a template child.
            node.type = None
        else:
            self.error("A template must define its own type", value)
        for key, attribute in attributes.items():
            if key in ("type", "use_template"):
                continue
            if key.removeprefix("not_") == "matches" and attribute.type != ValueType.REGEX:
                self.error("'matches' requires an ELCL regular expression", attribute)
            # A local negation replaces the corresponding positive template constraint (and vice versa).
            opposite = key[4:] if key.startswith("not_") else "not_" + key
            if opposite in node.options and opposite not in attributes:
                items = list(node.options.items())
                node.options = {key if k == opposite else k: v for k, v in items}
                node.options.pop(opposite + "_error", None)
            node.options[key] = native(attribute)
            node.option_locations[key] = attribute.location
        self.children(value, node, in_template)
        return node

    def merge(self, inherited: Node, local: Node, source: Value) -> None:
        """
        Apply a local child override to an inherited definition in place.

        Constraint replacements keep the inherited order. Replacing a positive
        constraint with its negation, or vice versa, removes the old custom error.
        Children merge by declaration spelling; relationship records are appended.

        :param source: Local declaration used to locate merge errors.
        :raises ConfValidationError: If an override changes the type or modifies alternatives.
        """
        if inherited.type == RuleType.ALTERNATIVES or local.type == RuleType.ALTERNATIVES:
            self.error("Alternative templates cannot be extended or overridden", source)
        if local.type is not None and local.type != inherited.type:
            self.error("A template child cannot change its type", source)
        for key, value in local.options.items():
            opposite = key[4:] if key.startswith("not_") else "not_" + key
            if opposite in inherited.options and opposite not in local.options:
                inherited.options = {key if k == opposite else k: v for k, v in inherited.options.items()}
                inherited.options.pop(opposite + "_error", None)
            inherited.options[key] = value
        inherited.option_locations.update(local.option_locations)
        inherited.keys.extend(deepcopy(local.keys))
        inherited.dependencies.extend(deepcopy(local.dependencies))
        for child in local.children:
            existing = next((c for c in inherited.children if c.spelling == child.spelling), None)
            if existing is None:
                inherited.children.append(child)
            else:
                self.merge(existing, child, source)
