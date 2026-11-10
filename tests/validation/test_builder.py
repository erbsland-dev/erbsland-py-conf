# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

import datetime as dt
import re
from dataclasses import FrozenInstanceError

import pytest

from erbsland.conf import (
    ConfValidationError,
    DateTime,
    DocumentBuilder,
    Name,
    NamePath,
    Time,
    TimeDelta,
    ValueType,
    loads,
)
from erbsland.conf.vr import DependencyMode, Rules, RulesBuilder, RuleType


def basic_builder():
    builder = RulesBuilder()
    server = builder.add_rule("server", RuleType.SECTION, title="Server")
    server.add_rule("port", int, minimum=1, maximum=65535, default=8080)
    server.add_rule("mode", str, in_=["http", "https"])
    server.add_rule(
        "tags", RuleType.VALUE_LIST, entry_type=str, entry_options={"minimum": 2, "title": "Tag"}, is_optional=True
    )
    return builder


@pytest.mark.parametrize(
    "document, valid",
    [
        ('[server]\nmode: "HTTP"\n', True),
        ('[server]\nmode: "https"\nport: 1\ntags: "ok", "good"\n', True),
        ('[server]\nmode: "https"\nport: 65535\ntags: "ok"\n', True),
        ('[server]\nmode: "ftp"\n', False),
        ('[server]\nmode: "http"\nport: 0\n', False),
        ('[server]\nmode: "http"\nport: yes\n', False),
        ('[server]\nmode: "http"\ntags: "x"\n', False),
        ('[server]\nmode: "http"\nunknown: 1\n', False),
        ("", False),
    ],
)
def test_elcl_and_keyword_builder_parity(document, valid):
    elcl = Rules.loads(
        """
[server]
type: "section"
title: "Server"
[server.port]
type: "integer"
minimum: 1
maximum: 65535
default: 8080
[server.mode]
type: "text"
in: "http", "https"
[server.tags]
type: "ValueList"
is_optional: Yes
[server.tags.vr_entry]
type: "text"
minimum: 2
title: "Tag"
"""
    )
    results = []
    for rules in (elcl, basic_builder().build()):
        doc = loads(document)
        if valid:
            assert rules.validate(doc, version=1) is None
            results.append(doc.to_test_value_tree())
            assert doc["server"].validation_rule.title == "Server"
        else:
            with pytest.raises(ConfValidationError) as error:
                rules.validate(doc, version=1)
            results.append((error.value.category, str(error.value.name_path)))
    assert results[0] == results[1]


def test_snapshots_paths_and_inputs_are_independent():
    builder = RulesBuilder()
    section = builder.add_rule(Name.create_regular("app"), RuleType.SECTION)
    choices = ["one", "two"]
    defaults = ["one", "two"]
    path = NamePath.from_text("item")
    item = section.add_rule(path, str, in_=choices, default="one")
    section.add_rule("list", RuleType.VALUE_LIST, entry_type=str, default=defaults)
    rules = builder.build()
    choices.append("three")
    defaults.append("three")
    path.append(Name.create_regular("changed"))
    item.configure_root(default="two")
    second_rules = builder.build()
    first, second = loads("[app]\n"), loads("[app]\n")
    rules.validate(first, 0)
    second_rules.validate(second, 0)
    assert first.get_text("app.item") == "one"
    assert second.get_text("app.item") == "two"
    assert first["app.list"].as_list(str) == ["one", "two"]
    assert first["app.list"][0] is not second["app.list"][0]
    rule = first["app.item"].validation_rule
    with pytest.raises(FrozenInstanceError):
        rule.title = "changed"
    with pytest.raises(FrozenInstanceError):
        rule.constraints[0].value = ("changed",)
    rule.name_path.append(Name.create_regular("changed"))
    assert str(rule.name_path) == "app.item"


def test_branches_alternatives_and_reset():
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_alternative("port", int, minimum=1)
    section = app.add_alternative("port", RuleType.SECTION)
    section.add_rule("name", str)
    builder.branch("app").configure_root(title="Application")
    rules = builder.build()
    for text in ("[app]\nport: 20\n", '[app.port]\nname: "http"\n'):
        rules.validate(loads(text), 0)
    with pytest.raises(ConfValidationError):
        app.build()
    with pytest.raises(ConfValidationError):
        app.reset()
    builder.reset()
    with pytest.raises(ConfValidationError):
        app.add_rule("stale", str)
    builder.add_rule("other", RuleType.NOT_VALIDATED)
    builder.build().validate(loads("[other]\nanything: 1\n"), 0)


def test_structural_helpers_keep_all_names_literal():
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_rule("vr_any", str)
    app.add_rule("vr_entry", int)
    app.add_rule("vr_literal_type", bool)
    app.add_rule("vr_vr_type", str)
    any_rule = app.add_any(int)
    any_rule.configure_name(starts="x_")
    rules = builder.build()
    doc = loads('[app]\nvr_any: "literal"\nvr_entry: 1\nvr_literal_type: yes\nvr_vr_type: "raw"\nx_one: 2\n')
    rules.validate(doc, 0)
    assert str(doc["app.vr_any"].validation_rule.name_path) == "app.vr_any"
    assert str(doc["app.x_one"].validation_rule.name_path) == "app.vr_any"
    with pytest.raises(ConfValidationError):
        rules.validate(
            loads('[app]\nvr_any: "literal"\nvr_entry: 1\nvr_literal_type: yes\nvr_vr_type: "raw"\nbad: 2\n'), 0
        )


def test_entry_and_wildcard_alternatives():
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    items = app.add_rule("items", RuleType.VALUE_LIST)
    items.add_entry_alternative(int, minimum=1)
    items.add_entry_alternative(str, equals="auto")
    app.add_any_alternative(bool)
    app.add_any_alternative(str, equals="auto")
    rules = builder.build()
    rules.validate(loads('[app]\nitems: 1, "auto", 3\nenabled: yes\nsetting: "auto"\n'), 0)
    with pytest.raises(ConfValidationError):
        rules.validate(loads('[app]\nitems: "bad"\n'), 0)


@pytest.mark.parametrize(
    "native_type, value",
    [
        (int, 3),
        (bool, True),
        (float, 1.25),
        (str, "x"),
        (bytes, b"\x01"),
        (dt.date, dt.date(2026, 1, 1)),
        (dt.time, dt.time(12, 30)),
        (Time, Time(12, 30, nanosecond=123456789)),
        (dt.datetime, dt.datetime(2026, 1, 1, 12, 30)),
        (DateTime, DateTime(2026, 1, 1, nanosecond=123456789)),
        (TimeDelta, TimeDelta()),
        (dt.timedelta, dt.timedelta(seconds=3)),
        (re.Pattern, re.compile("hello")),
    ],
)
def test_native_scalar_defaults(native_type, value):
    builder = RulesBuilder()
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_rule("value", native_type, default=value)
    rules = builder.build()
    doc = loads("[app]\n")
    rules.validate(doc, 1)
    assert doc["app.value"].is_default_value
    assert doc["app.value"].validation_rule.type == RuleType.from_type(native_type)
    if isinstance(value, (Time, DateTime)):
        assert doc["app.value"].native.nanosecond == 123456789
        value._nanosecond = 42
        assert doc["app.value"].native.nanosecond == 123456789


def test_relationship_builder_and_scopes():
    builder = RulesBuilder()
    servers = builder.add_rule("servers", RuleType.SECTION_LIST)
    server = servers.add_entry(RuleType.SECTION)
    server.add_rule("name", str)
    server.add_rule("port", int)
    builder.add_key("servers.vr_entry.name", name="server_names")
    builder.add_key("servers.vr_entry.name", "servers.vr_entry.port", name="server_pairs")
    app = builder.add_rule("app", RuleType.SECTION)
    app.add_rule("chosen", str, key="server_names", is_optional=True)
    app.add_rule("pair", str, key="server_pairs", is_optional=True)
    app.add_dependency(DependencyMode.IF, source="chosen", target="pair")
    rules = builder.build()
    good = '*[servers]\nname: "Main"\nport: 80\n[app]\nchosen: "main"\npair: "MAIN,80"\n'
    rules.validate(loads(good), 1)
    for bad in (good.replace('pair: "MAIN,80"', ""), good.replace('"main"', '"missing"')):
        with pytest.raises(ConfValidationError):
            rules.validate(loads(bad), 1)


@pytest.mark.parametrize(
    "options",
    [
        {"unknown": 1},
        {"minimum": True},
        {"in_": [1, True]},
        {"default": None},
        {"default": 1, "is_optional": True},
        {"minimum_error": "missing"},
        {"minimum": 2, "not_minimum": 1},
        {"maximum": 1, "minimum": 2},
        {"is_optional": 1},
        {"is_secret": "yes"},
        {"version": True},
        {"version": [1, 1]},
        {"entry_options": {"minimum": 2}},
        {"entry_type": str},
    ],
)
def test_builder_rejects_invalid_options(options):
    with pytest.raises(ConfValidationError):
        builder = RulesBuilder()
        app = builder.add_rule("app", RuleType.SECTION)
        app.add_rule("value", int, **options)
        builder.build()


@pytest.mark.parametrize("version", [-1, True, 1.0, None, "1"])
def test_document_version_is_explicit_nonnegative_integer(version):
    with pytest.raises(ConfValidationError):
        RulesBuilder().build().validate(loads(""), version)


def test_rule_files_and_preparsed_documents(tmp_path):
    path = tmp_path / "rules.elcl"
    path.write_text('[app.value]\ntype: "integer"\n', encoding="utf8")
    rules = Rules.load(path)
    rules.validate(loads("[app]\nvalue: 3\n"), 1)
    parsed = loads(path.read_text())
    Rules.from_document(parsed).validate(loads("[app]\nvalue: 4\n"), 1)
