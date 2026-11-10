# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf import ConfValidationError, loads
from erbsland.conf.vr import Rules, RulesBuilder, RuleType


@pytest.mark.parametrize(
    "declaration, target",
    [
        ("vr_literal_type", "type"),
        ("vr_literal_vr_any", "vr_any"),
        ("vr_literal_vr_entry", "vr_entry"),
        ("vr_literal_vr_name", "vr_name"),
        ("vr_literal_vr_literal_type", "vr_literal_type"),
        ("vr_vr_type", "vr_type"),
        ("vr_vr_vr_type", "vr_vr_type"),
        ("vr_literal_vr_vr_name", "vr_vr_name"),
    ],
)
def test_literal_defaults_paths_and_revalidation_match_builder(declaration, target):
    rules = Rules.loads(f'[app.{declaration}]\ntype: "integer"\ndefault: 7\nminimum: 10\n')
    builder = RulesBuilder()
    builder.add_rule("app", RuleType.SECTION).add_rule(target, int, default=7, minimum=10)
    for schema in (rules, builder.build()):
        doc = loads("[app]\n")
        schema.validate(doc, 1)
        value = doc[f"app.{target}"]
        assert value.native == 7 and value.is_default_value
        assert str(value.validation_rule.name_path) == f"app.{target}"
        schema.validate(doc, 1)
        assert doc[f"app.{target}"] is not value
        with pytest.raises(ConfValidationError) as error:
            schema.validate(loads(f"[app]\n{target}: 7\n"), 1)
        assert str(error.value.name_path) == f"app.{target}"


def test_nested_template_and_literal_alternative_metadata():
    rules = Rules.loads(
        """
[vr_template.settings]
type: "section"
[vr_template.settings.vr_literal_type]
type: "text"
[app.vr_literal_type]
use_template: "settings"
*[app.vr_literal_title]
type: "text"
*[app.vr_literal_title]
type: "integer"
"""
    )
    doc = loads('[app]\ntitle: 1\n[app.type]\ntype: "nested"\n')
    rules.validate(doc, 1)
    assert str(doc["app.title"].validation_rule.name_path) == "app.title"
    assert doc["app.title"].validation_rule.type == RuleType.INTEGER
    assert str(doc["app.type.type"].validation_rule.name_path) == "app.type.type"
    with pytest.raises(ConfValidationError) as error:
        rules.validate(loads("[app]\ntitle: 1\n[app.type]\n"), 1)
    assert str(error.value.name_path) == "app.type.type"


@pytest.mark.parametrize(
    "schema",
    [
        '[app.value]\ntype: "text"\n[app.vr_literal_value]\ntype: "text"\n',
        '[app.vr_vr_type]\ntype: "text"\n[app.vr_literal_vr_type]\ntype: "text"\n',
        '[vr_template.base]\ntype: "section"\n[vr_template.base.value]\ntype: "text"\n'
        '[app]\nuse_template: "base"\n[app.vr_literal_value]\ntype: "text"\n',
    ],
)
def test_literal_collisions_are_definition_errors(schema):
    with pytest.raises(ConfValidationError, match="Duplicate decoded target"):
        Rules.loads(schema)


def test_literal_controls_coexist_with_structural_rules_and_relationship_paths():
    rules = Rules.loads(
        """
*[vr_key]
name: "names"
key: "vr_entry.vr_entry.vr_entry"
[vr_literal_vr_entry]
type: "SectionList"
[vr_literal_vr_entry.vr_entry.vr_literal_vr_entry]
type: "text"
[app.vr_literal_vr_any]
type: "text"
key: "names"
is_optional: Yes
[app.vr_literal_vr_entry]
type: "integer"
is_optional: Yes
[app.vr_any]
type: "boolean"
*[app.vr_dependency]
mode: "if"
source: "vr_any"
target: "vr_entry"
"""
    )
    text = '*[vr_entry]\nvr_entry: "selected"\n[app]\nvr_any: "selected"\nvr_entry: 5\nextra: yes\n'
    doc = loads(text)
    rules.validate(doc, 1)
    assert doc["app.vr_any"].validation_rule.type == RuleType.TEXT
    assert doc["app.extra"].validation_rule.type == RuleType.BOOLEAN
    assert str(doc["vr_entry"][0]["vr_entry"].validation_rule.name_path) == "vr_entry.vr_entry.vr_entry"
    with pytest.raises(ConfValidationError, match="dependency"):
        rules.validate(loads(text.replace("vr_entry: 5\n", "")), 1)
