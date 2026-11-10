*******************************************
Accessing the Values in the Parsed Document
*******************************************

Once parsed, a configuration file becomes a :class:`~erbsland.conf.Document` instance,  
which itself is derived from :class:`~erbsland.conf.Value`.  

You can think of it as a **tree of values and sections**, and you can access these values in several different ways depending on your needs.  

Accessing Values via Name-Path
==============================

If you know the fixed names of the values in your configuration, you can access them directly using a **string-based name-path**:

.. code-block:: python
    :emphasize-lines: 6-7

    import erbsland.conf as elcl

    try:
        doc = elcl.load("configuration.elcl")

        server_port = doc["server.port"].as_int()
        server_host = doc["server.host"].as_text()

        # ...
    except elcl.Error as e:
        print(f"Failed to load configuration: {e}")

The path is always resolved **relative to the instance** you access it from.  

.. note::

    When you use a string name-path, it must be parsed and validated on **every lookup**.  
    If you repeatedly access the same values, it is more efficient to pre-compile the name-paths once:  

    .. code-block:: python

        SERVER_PORT = elcl.NamePath.from_text("server.port")
        SERVER_HOST = elcl.NamePath.from_text("server.host")

    This way, any syntax errors are raised early (at definition time), and lookups are faster.

Accessing Values via Index
==========================

Every :class:`~erbsland.conf.Value` also behaves like a **Python list**,  
so you can access elements using an index:

.. code-block:: python

    first_server = doc["server"][0]
    last_server = doc["server"][-1]

The difference to regular Python lists is that errors are not raised as :class:`IndexError`,
but as :class:`~erbsland.conf.error.ConfValueNotFound`.

.. note::

    For convenience, you can also use the :data:`~erbsland.conf.Value.first`
    and :data:`~erbsland.conf.Value.last` properties.

Iterating over Value and Section Lists
======================================

Every value is iterable. This makes it easy to loop through lists of sections or values:  

.. code-block:: python

    for server_value in doc["server"]:
        port = server_value["port"].as_int()
        host = server_value["host"].as_text()
        # ...

This is especially useful when your configuration defines multiple sections of the same kind  
(for example, multiple servers, clients, or plugins).  

.. button-ref:: working_with_types
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Working with Value Types →
