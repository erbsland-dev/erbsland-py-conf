****************
Validation Rules
****************

Validation rules check an entire configuration before the application uses it.
They describe allowed names, value types, constraints, defaults, and relationships
between values. A schema is closed: values without a matching rule are rejected.

Define rules in Python or in an ELCL document. Both forms use the same compiler
and validation engine. Compile rules once and reuse them for multiple documents.

Building Rules in Python
========================

Use native Python scalar types and keyword arguments:

.. code-block:: python

    import erbsland.conf as elcl
    from erbsland.conf import vr

    builder = vr.RulesBuilder()
    server = builder.add_rule("server", vr.RuleType.SECTION, title="Server settings")
    server.add_rule("port", int, minimum=1, maximum=65535, default=8080)
    server.add_rule("mode", str, in_=["http", "https"])
    server.add_rule(
        "tags",
        vr.RuleType.VALUE_LIST,
        entry_type=str,
        entry_options={"minimum": 2},
        is_optional=True,
    )
    rules = builder.build()

    document = elcl.loads('[server]\nmode: "https"\n')
    rules.validate(document, version=1)
    assert document.get_int("server.port") == 8080

``build()`` checks the whole definition and returns an immutable snapshot.
It does not reset the builder. Subsequent edits cannot change previously built
rules. Invalid definitions and document validation failures raise
:class:`~erbsland.conf.ConfValidationError`.

Declare parent sections before their children. ``add_rule()`` returns a branch
view, whose paths are relative to that rule. ``builder.branch("server")`` retrieves
an existing branch. ``configure_root()`` updates the rule represented by a view.
Only the original builder can ``build()`` or ``reset()``; resetting invalidates
existing branch views.

Native scalar types include ``int``, ``bool``, ``float``, ``str``, ``bytes``,
``datetime.date``, ``datetime.time``, ``datetime.datetime``, ``datetime.timedelta``,
``re.Pattern``, and the library's ``Time``, ``DateTime`` and ``TimeDelta`` types.
Use ``RuleType`` for sections, lists, matrices, any scalar (``VALUE``), and
unvalidated branches (``NOT_VALIDATED``). ELCL type identifiers such as
``"value_list"`` are accepted too. Values are checked strictly: a boolean does
not satisfy an integer rule.

Reading ELCL Rules
==================

The same schema can be written as ordinary ELCL:

.. code-block:: erbsland-conf

    [server]
    type: "section"
    title: "Server settings"

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

Load a rules file with ``vr.Rules.load("rules.elcl")`` or text with
``vr.Rules.loads(text)``. To use a parser with customized source resolution,
access policies or signature handling, parse the rules normally and pass the
result to ``vr.Rules.from_document(document)``.

ELCL rules support templates, alternatives, implicit ancestor sections,
variable names, keys and dependencies. The `ELCL validation specification`_
describes the language. List and matrix definitions require an explicit
``vr_entry``; Python's ``entry_type=`` creates this entry rule.

Literal Configuration Names
===========================

An attribute such as ``type`` cannot share an ELCL section with a child section
of the same name. Escape that child declaration with ``vr_literal_``:

.. code-block:: erbsland-conf

    [server]
    type: "section"
    title: "Server settings"

    [server.vr_literal_type]
    type: "text"

    [server.vr_literal_title]
    type: "text"
    default: "Main server"

These rules target ``server.type`` and ``server.title``. Exactly one prefix is
removed: ``vr_literal_vr_any`` targets a field literally named ``vr_any``.
The legacy escape ``vr_vr_type`` targets ``vr_type``. Declarations resolving to
the same name are rejected, including collisions introduced through templates.

Python builder paths are always literal. Use ``server.add_rule("type", str)``
directly. A Python declaration named ``vr_literal_type`` targets that exact
configuration name.

Dependencies and index paths always use actual configuration names.
In key paths, ``vr_entry`` is structural only immediately after a section-list
rule. A list literally named ``vr_entry`` can therefore be indexed using
``"vr_entry.vr_entry.type"``.

Entries, Alternatives and Variable Names
========================================

Use dedicated helpers to keep structural roles separate from literal names:

.. code-block:: python

    builder = vr.RulesBuilder()
    users = builder.add_rule("users", vr.RuleType.SECTION_LIST)
    user = users.add_entry(vr.RuleType.SECTION)
    user.add_rule("name", str, minimum=1)

    settings = builder.add_rule("settings", vr.RuleType.SECTION)
    settings.add_rule("vr_any", str, default="literal field")
    variable = settings.add_any(int, minimum=0)
    variable.configure_name(starts="counter_")

    settings.add_alternative("port", int, minimum=1, maximum=65535)
    settings.add_alternative("port", str, equals="auto")

``add_entry_alternative()`` and ``add_any_alternative()`` create alternatives
for entries and wildcard rules. ``configure_name()`` applies text constraints to
the matched name; it also works on ordinary named rules.

Alternatives are tried in declaration order. The first whose own type, version
and constraints match is selected. Child validation follows selection and does
not backtrack to another alternative.

``ValueList`` accepts a scalar as a one-entry list. ``ValueMatrix`` accepts a
scalar as a one-by-one matrix and a flat list as a one-column matrix. This does
not change the stored value type. Matrix size constraints take a pair of integers:
rows followed by columns. Column checks apply to every row, including ragged rows.
Negated matrix constraints negate each dimension's check.

Constraints and Diagnostics
===========================

Keyword names match ELCL: ``minimum``, ``maximum``, ``equals``, ``multiple``,
``starts``, ``ends``, ``contains``, ``chars``, ``matches``, and ``key``.
Use ``in_`` for the ELCL ``in`` constraint because ``in`` is a Python keyword.
Supported ``not_`` forms negate constraints; ``not_chars`` forbids any occurrence
of the specified characters.

Constraints run in keyword order, after type checking. Attach a constraint error
with, for example, ``minimum_error="Choose a positive port"``. The corresponding
constraint must exist. Constraint errors override the node-level ``error``;
neither overrides structural or type errors. Empty custom messages are ignored.

Text comparisons use Unicode ``str.casefold()`` unless ``case_sensitive=True``.
Character sets are always case-sensitive. ``matches`` uses Python's ``re``
dialect and partial matching via ``search()``; its flags are independent of
``case_sensitive``. Python declarations accept a pattern string or compiled
``re.Pattern``; ELCL declarations require a regex literal. Anchor patterns when
a whole-value match is intended. Python's regex engine does not impose a timeout.

Floating equality and membership use ``math.isclose`` with relative and absolute
tolerances of eight times ``sys.float_info.epsilon``. Floating multiples compare
the quotient to the nearest integer using the same tolerances. NaN matches NaN
for equality, but cannot satisfy a minimum or maximum. Zero and nonfinite
divisors are rejected. Text lengths count Unicode code points, not encoded bytes.

Date-time bounds compare instants with nanosecond precision. Naive Python
date-times and ELCL date-times without an offset are interpreted as UTC for
these comparisons; explicit offsets are respected.

Indexes and Dependencies
========================

.. code-block:: python

    builder.add_key("users.vr_entry.name", name="user_names")
    settings.add_rule("owner", str, key="user_names", is_optional=True)
    settings.add_rule("token", str, is_optional=True, is_secret=True)
    settings.add_dependency(
        vr.DependencyMode.IF, source="owner", target="token",
        error="An owner requires a token.",
    )

``add_key()`` enforces uniqueness in a section list. Multiple paths form a
composite key; all paths must address the same list. A named index is visible
inside the branch declaring it, with nearer definitions shadowing ancestors.
References can select a composite component using ``"index_name[0]"`` or refer
to the whole composite as comma-separated text. Index case sensitivity governs
both uniqueness and reference matching.

Dependencies support ``IF``, ``IF_NOT``, ``OR``, ``XOR``, ``XNOR`` and ``AND``.
Source and target each accept one path or a sequence of paths; each side is
configured if any referenced node was explicitly supplied. Defaults do not count.
Paths are relative to the declaring branch and must reference conditionally
present nodes, without crossing lists or alternative definitions.

Mutation, Reuse and Metadata
============================

``rules.validate(document_or_section, version=1)`` requires an explicit,
nonnegative integer version and returns ``None`` on success. The application
chooses the version; it is separate from ELCL's ``@version``.

Validation inserts defaults and attaches metadata in place. Default values must
match the declared type but bypass ordinary constraints. Defaults and optionality
cannot be combined. A missing optional parent does not create default children.

Each value exposes:

* ``validation_rule``: the selected read-only rule, or ``None``.
* ``is_validated``: whether the node has passed local validation.
* ``is_default_value``: whether validation inserted it as a default.
* ``is_secret``: whether the selected rule marks it as sensitive.

Rule metadata includes title, description, constraints, children, location and
``name_path``, plus ``default`` and read-only ``version_constraints``.
Rule paths are symbolic and relative to the validated root:
``items.vr_entry.type`` represents the field in any list entry. Value paths
retain concrete list indexes and their full document ancestry.

Validation failures preserve source locations and concrete configuration paths.
Generated diagnostics do not include supplied secret values, and ``str(value)``
masks values marked secret. Native getters intentionally still return their
contents; conformance-test serializers are intended for trusted test data.

Revalidation removes previous defaults and refreshes metadata only within the
selected subtree. Rule objects can be shared between independent validations;
their indexes and traversal state are per call. Do not concurrently validate
the same mutable document. Failure can leave partial metadata or defaults;
successful validation of the whole document is required before using it.

.. _ELCL validation specification: https://config-lang.erbsland.dev/validation-rules/index.html

.. button-ref:: troubleshooting
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Troubleshooting →
