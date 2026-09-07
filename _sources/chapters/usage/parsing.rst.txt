******************
Parsing a Document
******************

In its simplest form, you can parse a document like this:

.. code-block:: python

    import erbsland.conf as elcl

    try:
        doc = elcl.load("configuration.elcl")
        server_port = doc["server.port"].as_int()
        # ...
    except elcl.Error as e:
        print(f"Failed to load configuration: {e}")

This approach is usually all you need: it loads the document, validates it, and gives you access to its values.

Using a Parser Instance
=======================

If you want more control over how documents are handled—for example:

* controlling how included configuration files are resolved,
* limiting access to the filesystem, or
* verifying a document with a signature check—

you can create an explicit :class:`~erbsland.conf.parser.Parser` instance instead.

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

The same ``parser`` instance can be reused to parse multiple documents.
This is useful if you need to apply the same access policies or validation rules consistently across different files.

.. button-ref:: accessing_values
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Accessing the Values in the Parsed Document →

