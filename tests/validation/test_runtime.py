# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

from concurrent.futures import ThreadPoolExecutor

import pytest

from erbsland.conf import ConfValidationError, ValueType, loads
from erbsland.conf.vr import Rules, RulesBuilder, RuleType


def test_defaults_revalidation_and_subtree_isolation():
    rules = Rules.loads(
        """
[value]
type: "integer"
default: 0
minimum: 1
"""
    )
    doc = loads("[first]\n[second]\n")
    rules.validate(doc["first"], 1)
    first_default = doc["first.value"]
    assert first_default.is_default_value and first_default.is_validated
    assert doc.get("second.value") is None
    rules.validate(doc["second"], 1)
    rules.validate(doc["first"], 1)
    assert first_default is not doc["first.value"]
    assert first_default.parent is None
    assert doc["second.value"].is_default_value
    assert str(doc["first.value"].validation_rule.name_path) == "value"
    assert str(doc["first.value"].name_path) == "first.value"


def test_version_change_removes_old_defaults_and_metadata():
    old = Rules.loads('[app.x]\ntype: "integer"\ndefault: 1\nversion: 1\n')
    doc = loads("[app]\n")
    old.validate(doc, 1)
    assert doc.get("app.x") is not None
    old.validate(doc, 2)
    assert doc.get("app.x") is None
    skip = Rules.loads('[app]\ntype: "NotValidated"\n')
    skip.validate(doc, 2)
    assert not doc["app"].is_validated
    assert doc.is_validated


def test_optional_missing_parent_does_not_create_defaults():
    rules = Rules.loads('[app]\ntype: "section"\nis_optional: yes\n[app.x]\ntype: "text"\ndefault: "x"\n')
    doc = loads("")
    rules.validate(doc, 0)
    assert len(doc) == 0


def test_empty_schema_is_closed():
    rules = Rules.loads("")
    rules.validate(loads(""), 0)
    with pytest.raises(ConfValidationError):
        rules.validate(loads("[app]\n"), 0)


def test_first_alternative_commits_before_validating_children():
    rules = Rules.loads(
        """
*[app]
type: "section"
[app.first]
type: "integer"
*[app]
type: "section"
[app.second]
type: "integer"
"""
    )
    with pytest.raises(ConfValidationError) as error:
        rules.validate(loads("[app]\nsecond: 2\n"), 0)
    assert str(error.value.name_path) == "app.first"


def test_list_alternatives_do_not_backtrack_on_entry_failure():
    rules = Rules.loads(
        """
*[app.items]
type: "ValueList"
[app.items.vr_entry]
type: "integer"
*[app.items]
type: "ValueList"
[app.items.vr_entry]
type: "text"
"""
    )
    with pytest.raises(ConfValidationError):
        rules.validate(loads('[app]\nitems: "text"\n'), 0)


def test_errors_follow_document_and_constraint_order():
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_rule(
        "a", int, maximum=10, minimum=1, not_equals=0, error="general", minimum_error="small", not_equals_error="zero"
    )
    app.add_rule("b", int, maximum=10, minimum=1)
    with pytest.raises(ConfValidationError) as error:
        builder.build().validate(loads("[app]\nb: 0\na: 0\n"), 0)
    assert str(error.value.name_path) == "app.b"
    with pytest.raises(ConfValidationError, match="small"):
        builder.build().validate(loads("[app]\na: 0\nb: 1\n"), 0)
    with pytest.raises(ConfValidationError, match="Expected Integer"):
        builder.build().validate(loads('[app]\na: "bad"\nb: 1\n'), 0)


def test_unknown_nodes_are_reported_after_local_constraints():
    rules = Rules.loads('[app.n]\ntype: "integer"\nminimum: 1\n')
    with pytest.raises(ConfValidationError) as error:
        rules.validate(loads("[app]\nunknown: 1\nn: 0\n"), 0)
    assert str(error.value.name_path) == "app.n"


def test_scalar_list_and_matrix_storage_and_metadata():
    rules = Rules.loads(
        """
[app.list]
type: "ValueList"
[app.list.vr_entry]
type: "text"
[app.matrix]
type: "ValueMatrix"
equals: 1, 1
[app.matrix.vr_entry]
type: "integer"
"""
    )
    doc = loads('[app]\nlist: "only"\nmatrix: 7\n')
    rules.validate(doc, 0)
    assert doc["app.list"].type == ValueType.TEXT
    assert doc["app.matrix"].type == ValueType.INTEGER
    assert doc["app.list"].validation_rule.type == RuleType.VALUE_LIST


def test_local_indexes_do_not_leak_between_instances_or_documents():
    rules = Rules.loads(
        """
[groups]
type: "SectionList"
*[groups.vr_entry.vr_key]
name: "item"
key: "items.vr_entry.id"
[groups.vr_entry.items]
type: "SectionList"
[groups.vr_entry.items.vr_entry.id]
type: "text"
[groups.vr_entry.chosen]
type: "text"
key: "item"
"""
    )

    def validate(identifier):
        doc = loads(f'*[groups]\nchosen: "{identifier}"\n*[groups.items]\nid: "{identifier}"\n')
        rules.validate(doc, 0)
        return doc["groups"][0].get_text("chosen")

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(validate, ["first", "second", "third", "fourth"])) == [
            "first",
            "second",
            "third",
            "fourth",
        ]
    bad = '*[groups]\nchosen: "first"\n*[groups.items]\nid: "first"\n*[groups]\nchosen: "first"\n*[groups.items]\nid: "second"\n'
    with pytest.raises(ConfValidationError):
        rules.validate(loads(bad), 0)


@pytest.mark.parametrize(
    "mode, accepted",
    [
        ("if", [True, True, False, True]),
        ("if_not", [True, True, True, False]),
        ("or", [False, True, True, True]),
        ("xor", [False, True, True, False]),
        ("xnor", [True, False, False, True]),
        ("and", [False, False, False, True]),
    ],
)
def test_dependency_truth_tables_exclude_defaults(mode, accepted):
    rules = Rules.loads(
        f"""
[app.a]
type: "integer"
default: 1
[app.b]
type: "integer"
default: 1
*[app.vr_dependency]
mode: "{mode}"
source: "a"
target: "b"
"""
    )
    for index, text in enumerate(("", "b: 1\n", "a: 1\n", "a: 1\nb: 1\n")):
        doc = loads("[app]\n" + text)
        if accepted[index]:
            rules.validate(doc, 0)
        else:
            with pytest.raises(ConfValidationError):
                rules.validate(doc, 0)


def test_secrets_are_not_in_errors_or_value_strings():
    rules = Rules.loads('[app.password]\ntype: "text"\nis_secret: yes\nminimum: 10\n')
    secret = "PRIVATE_SECRET"
    doc = loads(f'[app]\npassword: "{secret}"\n')
    rules.validate(doc, 0)
    assert doc["app.password"].is_secret
    assert secret not in str(doc["app.password"])
    assert doc.get_text("app.password") == secret
    with pytest.raises(ConfValidationError) as error:
        rules.validate(loads('[app]\npassword: "HIDDEN"\n'), 0)
    assert "HIDDEN" not in str(error.value)


def test_branch_uniqueness_is_checked_before_unrelated_branch_constraints():
    rules = Rules.loads(
        """
*[first.vr_key]
key: "items.vr_entry.name"
[first.items]
type: "SectionList"
[first.items.vr_entry.name]
type: "text"
[second.value]
type: "integer"
minimum: 1
"""
    )
    doc = loads('*[first.items]\nname: "same"\n*[first.items]\nname: "same"\n[second]\nvalue: 0\n')
    with pytest.raises(ConfValidationError, match="Duplicate key") as error:
        rules.validate(doc, 1)
    assert str(error.value.name_path) == "first.items[1]"


def test_key_constraints_precede_dependencies_in_the_same_branch():
    rules = Rules.loads(
        """
*[vr_key]
key: "items.vr_entry.name"
name: "names"
[items]
type: "SectionList"
[items.vr_entry.name]
type: "text"
[app.chosen]
type: "text"
is_optional: Yes
key: "names"
key_error: "Unknown selection"
[app.token]
type: "text"
is_optional: Yes
*[app.vr_dependency]
mode: "if"
source: "chosen"
target: "token"
error: "Missing token"
"""
    )
    with pytest.raises(ConfValidationError, match="Unknown selection"):
        rules.validate(loads('*[items]\nname: "known"\n[app]\nchosen: "unknown"\n'), 1)
    with pytest.raises(ConfValidationError, match="Missing token"):
        rules.validate(loads('*[items]\nname: "known"\n[app]\nchosen: "known"\n'), 1)
