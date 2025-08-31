
Erbsland Configuration Parser for Python
========================================

Welcome to the implementation of the **Erbsland Configuration Language Parser**—a modern and robust configuration parser built for Python 3.12 and beyond. This implementation is designed to be secure, minimal in dependencies, and easy to integrate into your existing projects.

All you need is a Python 3.12 or newer – there are no external dependencies, no hassle.

Topics
------

.. grid:: 2
    :margin: 4 4 0 0
    :gutter: 1

    .. grid-item-card:: :fas:`user;sd-text-success` How to Use the Parser
        :link: chapters/usage/index
        :link-type: doc

        Learn how to use the parser in your application.

    .. grid-item-card:: :fas:`code;sd-text-success` API Reference
        :link: chapters/reference/index
        :link-type: doc

        Access detailed reference material on all classes, methods, and core components of the parser’s API.

    .. grid-item-card:: :fas:`book-open;sd-text-success` Configuration Language Documentation
        :link: https://config-lang.erbsland.dev

        Dive into the formal documentation of the *Erbsland Configuration Language* to understand its syntax and features.

    .. grid-item-card:: :fas:`landmark;sd-text-success` License
        :link: chapters/license
        :link-type: doc

        Familiarize yourself with the terms of use under the Apache 2.0 license.

Quick Usage Overview
====================

.. code-block:: python
    :caption: Minimal Example

    import erbsland.conf as elcl
    doc = elcl.load("config.elcl")
    print(doc.get_int("server.port"))

.. literalinclude:: chapters/usage/examples/quick-intro.py
    :language: python
    :caption: A More Realistic Example

Contents at a Glance
====================

.. toctree::
    :maxdepth: 3

    chapters/usage/index
    chapters/reference/index
    chapters/contribute/index
    chapters/contribute/code-of-conduct
    chapters/contribute/code-style
    chapters/contribute/write-a-unittest
    chapters/goals
    chapters/license

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

