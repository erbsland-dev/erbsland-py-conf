
Erbsland Configuration Parser for Python
========================================

Welcome to the implementation of the **Erbsland Configuration Language Parser**—a modern and robust configuration parser built for Python 3.12 and beyond. This implementation is designed to be secure, minimal in dependencies, and easy to integrate into your existing projects.

All you need is a Python 3.12 or newer – there are no external dependencies, no hassle.

.. button-ref:: chapters/usage/index
    :ref-type: doc
    :color: success
    :align: center
    :expand:
    :class: sd-fs-2 sd-font-weight-bold sd-p-3

    Read how to use the parser →

Topics
------

.. grid:: 3
    :margin: 4 4 0 0
    :gutter: 1

    .. grid-item-card:: :fas:`download;sd-text-success` Installation
        :link: chapters/installation
        :link-type: doc

        Details about installing the parser.

    .. grid-item-card:: :fas:`user;sd-text-success` How to Use the Parser
        :link: chapters/usage/index
        :link-type: doc

        Learn how to use the parser in your application.

    .. grid-item-card:: :fas:`code;sd-text-success` API Reference
        :link: chapters/reference/index
        :link-type: doc

        Reference material on all classes and methods of the parser’s API.

    .. grid-item-card:: :fas:`book-open;sd-text-success` Configuration Language Documentation
        :link: https://config-lang.erbsland.dev

        The formal documentation of the *Erbsland Configuration Language*.

    .. grid-item-card:: :fas:`layer-group;sd-text-success` Requirements
        :link: chapters/requirements
        :link-type: doc

        The requirements needed to use this parser.

    .. grid-item-card:: :fas:`landmark;sd-text-success` License
        :link: chapters/license
        :link-type: doc

        Familiarize yourself with the terms of use under the Apache 2.0 license.

Quick Usage Overview
====================

Installation
------------

.. code-block:: shell

    pip install erbsland-conf

Minimal Example
---------------

.. code-block:: python

    import erbsland.conf as elcl
    doc = elcl.load("config.elcl")
    print(doc.get_int("server.port"))

A More Realistic Example
------------------------

.. literalinclude:: chapters/usage/examples/quick-intro.py
    :language: python

Contents at a Glance
====================

.. toctree::
    :maxdepth: 3

    chapters/installation
    chapters/usage/index
    chapters/reference/index
    chapters/contribute/index
    chapters/contribute/code-of-conduct
    chapters/contribute/code-style
    chapters/contribute/write-a-unittest
    chapters/requirements
    chapters/goals
    chapters/license

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

