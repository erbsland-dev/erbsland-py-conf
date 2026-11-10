# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

import datetime as dt

import pytest

from erbsland.conf import ConfValidationError, DateTime, loads
from erbsland.conf.vr import Rules, RulesBuilder, RuleType


@pytest.mark.parametrize("kind", [RuleType.VALUE_LIST, RuleType.VALUE_MATRIX, RuleType.SECTION_LIST])
def test_inactive_entry_rules_do_not_validate_entries(kind):
    builder = RulesBuilder()
    items = builder.add_rule("items", kind)
    entry = items.add_entry(RuleType.SECTION if kind == RuleType.SECTION_LIST else int, version=2)
    if kind == RuleType.SECTION_LIST:
        entry.add_rule("value", int)
    rules = builder.build()
    # Root scalar assignments are unavailable in ELCL; validate a selected section.
    doc = loads("*[items]\nvalue: 1\n") if kind == RuleType.SECTION_LIST else loads("[app]\nitems: 1, 2\n")
    root = doc if kind == RuleType.SECTION_LIST else doc["app"]
    rules.validate(root, 2)
    with pytest.raises(ConfValidationError, match="Unexpected value"):
        rules.validate(root, 1)


def test_name_constraints_follow_version_filters():
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_any(int).configure_name(starts="new_", minimum_version=2)
    rules = builder.build()
    rules.validate(loads("[app]\nold: 1\n"), 1)
    with pytest.raises(ConfValidationError) as error:
        rules.validate(loads("[app]\nold: 1\n"), 2)
    assert str(error.value.name_path) == "app.old"


def test_name_keys_use_names_and_report_value_paths():
    rules = Rules.loads(
        """
*[vr_key]
name: "names"
key: "users.vr_entry.name"
[users]
type: "SectionList"
[users.vr_entry.name]
type: "text"
[permissions.vr_any]
type: "integer"
[permissions.vr_any.vr_name]
key: "names"
key_error: "Unknown user name"
"""
    )
    rules.validate(loads('*[users]\nname: "Alice"\n[permissions]\nalice: 5\n'), 1)
    with pytest.raises(ConfValidationError, match="Unknown user name") as error:
        rules.validate(loads('*[users]\nname: "Alice"\n[permissions]\nbob: 5\n'), 1)
    assert str(error.value.name_path) == "permissions.bob"


def test_name_constraints_are_rejected_on_entry_alternatives():
    builder = RulesBuilder()
    items = builder.add_rule("items", RuleType.VALUE_LIST)
    items.add_entry_alternative(str).configure_name(starts="wrong")
    with pytest.raises(ConfValidationError, match="named or wildcard"):
        builder.build()


@pytest.mark.parametrize("type_name", ["int_eger", "i n t e g e r", "_integer", "integer_", "value__list"])
def test_malformed_type_identifiers_are_not_aliases(type_name):
    with pytest.raises(ConfValidationError, match="Unknown validation rule type"):
        Rules.loads(f'[app.value]\ntype: "{type_name}"\n')


@pytest.mark.parametrize("type_name", ["VALUE LIST", "ValueList", "value_list"])
def test_type_aliases(type_name):
    assert RuleType.from_type(type_name) == RuleType.VALUE_LIST


def test_datetime_bounds_and_metadata_preserve_nanoseconds():
    lower = DateTime(2026, 1, 1, nanosecond=123456780)
    upper = DateTime(2026, 1, 1, nanosecond=123456789)
    builder = RulesBuilder()
    value = builder.add_rule("value", dt.datetime, minimum=lower, maximum=upper, default=upper, version=[1, 2])
    rules = builder.build()
    rule = rules.root.children[0]
    # Both public views and later builder edits must be independent of the snapshot.
    rule.constraints[0].value._nanosecond = 0
    rule.default._nanosecond = 0
    assert rule.constraints[0].value.nanosecond == 123456780
    assert rule.default.nanosecond == 123456789
    with pytest.raises(TypeError):
        rule.version_constraints["version"] = (3,)
    docs = [loads("[app]\n"), loads("[app]\n")]
    for doc in docs:
        rules.validate(doc["app"], 1)
    docs[0]["app.value"].native._nanosecond = 1
    assert docs[1]["app.value"].native.nanosecond == 123456789
    with pytest.raises(ConfValidationError, match="minimum"):
        rules.validate(loads("[app]\nvalue: 2026-01-01 00:00:00.123456779\n")["app"], 1)
    value.configure_root(minimum=upper, maximum=lower)
    with pytest.raises(ConfValidationError, match="minimum must not exceed"):
        builder.build()


def test_datetime_bounds_compare_utc_offsets_and_naive_values():
    builder = RulesBuilder()
    builder.add_rule(
        "value",
        dt.datetime,
        minimum=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone(dt.timedelta(hours=1))),
        maximum=dt.datetime(2026, 1, 1, 11),
    )
    rules = builder.build()
    rules.validate(loads("[app]\nvalue: 2026-01-01 11:00:00z\n")["app"], 1)
    with pytest.raises(ConfValidationError):
        rules.validate(loads("[app]\nvalue: 2026-01-01 11:00:00+01:00\n")["app"], 1)


def test_invalid_entry_option_keys_raise_definition_errors():
    with pytest.raises(ConfValidationError, match="option names"):
        RulesBuilder().add_rule("values", RuleType.VALUE_LIST, entry_type=int, entry_options={1: 2})


def test_template_child_overrides_preserve_constraint_order():
    rules = Rules.loads(
        """
[vr_template.base]
type: "section"
[vr_template.base.value]
type: "integer"
minimum: 1
minimum_error: "inherited minimum"
maximum: 10
maximum_error: "inherited maximum"
[app]
use_template: "base"
[app.value]
not_minimum: 2
not_minimum_error: "local negation"
"""
    )
    value_rule = rules.root.children[0].children[0]
    assert [c.name for c in value_rule.constraints] == ["not_minimum", "maximum"]
    with pytest.raises(ConfValidationError, match="local negation"):
        rules.validate(loads("[app]\nvalue: 20\n"), 1)
    rules.validate(loads("[app]\nvalue: 1\n"), 1)


def test_template_definition_error_has_insertion_path_and_original_location():
    text = '[vr_template.base]\ntype: "integer"\nminimum: "bad"\n[app.vr_literal_type]\nuse_template: "base"\n'
    document = loads(text)
    with pytest.raises(ConfValidationError) as error:
        Rules.from_document(document)
    assert str(error.value.name_path) == "app.vr_literal_type.minimum"
    assert error.value.location == document["vr_template.base.minimum"].location


def test_key_definition_error_uses_escaped_definition_path():
    text = '[app.vr_literal_type]\ntype: "text"\nkey: "missing"\n'
    with pytest.raises(ConfValidationError) as error:
        Rules.loads(text)
    assert str(error.value.name_path) == "app.vr_literal_type.key"
