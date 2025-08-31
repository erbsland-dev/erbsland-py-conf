
******
Parser
******

The parser interface :class:`Parser<erbsland.conf.parser.Parser>` provides an object interface, where you can configure the parser to parse one or multiple configuration files. For convinience and to match the expectations for Python interfaces, there are also the methods :func:`load<erbsland.conf.parser.load>` and :func:`loads<erbsland.conf.parser.loads>` which load and parse a configuration file using the default settings.

Usage
=====

.. code-block:: python

    import erbsland.conf as elcl

    try:
        doc = elcl.load("configuration.elcl")
        # ...
    except elcl.Error as e:
        print(f"Failed to load configuration: {e}")

.. code-block:: python

    import erbsland.conf as elcl

    parser = elcl.Parser()
    flags = (
        elcl.AccessFeature.SAME_DIRECTORY |
        elcl.AccessFeature.SUBDIRECTORIES |
        elcl.AccessFeature.LIMIT_SIZE |
        elcl.AccessFeature.REQUIRE_SUFFIX
    )
    access_check = elcl.FileAccessCheck(flags)
    parser.access_check = access_check

    try:
        doc = parser.parse("configuration.elcl")
        # ...
    except elcl.Error as e:
        print(f"Failed to load configuration: {e}")


Interface
=========

.. autofunction:: erbsland.conf.load

.. autofunction:: erbsland.conf.loads

.. autoclass:: erbsland.conf.Parser
    :members:

