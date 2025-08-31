.. index::
    !single: Goals

*****
Goals
*****

.. grid:: 2

    .. grid-item-card:: :fas:`link-slash;sd-text-success` No Dependencies
        :shadow: md

        Requires only Python 3.12 or newer.

    .. grid-item-card:: :fas:`code;sd-text-success` Expressive Interface
        :shadow: md

        Reduces boilerplate in user code, making integration clean and concise.

Overview
========

This Python parser is one of the main implementations of the *Erbsland Configuration Language* (ELCL).
Its primary goals are **security, robustness, and full feature coverage**—delivered in a clean and understandable codebase.

It is both:

* **Production-ready**: safe to use in real-world systems.
* **Educational**: a reference for developers implementing their own ELCL parsers.

Full Feature Coverage
=====================

The parser supports the **entire ELCL specification**, including:

* Core features: names, values, and sections
* Standard features: multiline values, byte counts, and value lists
* Advanced features: regular expressions, code blocks, and time deltas

Dependency-Free
===============

The parser is intentionally designed with **zero external dependencies**:

* No third-party libraries are required.
* You can install and run it anywhere Python 3.12+ is available.

Modern, Readable Python
=======================

The codebase is written in **modern Python (3.12+)**, with a focus on readability:

* Fully annotated with type hints for clarity and IDE support
* Explicit rather than “clever”—favoring clarity over abstraction
* Structured so you can easily read, understand, and extend it without guesswork

Robustness Over Performance
===========================

Parsing configuration files is rarely the main performance bottleneck in a system.
Instead, **robust behavior** is critical for reliability:

* Correctness, consistency, and transparency always come before raw speed.
* Error messages are clear and actionable, helping users quickly identify and fix mistakes.
* Performance optimizations are applied where useful, but never at the cost of readability or correctness.
