
**************
Error Handling
**************

We designed the error handling for the API to allow you developing tools as quickly as possible. For this reason, all *runtime* errors raised by the API are derived from :class:`~erbsland.conf.error.Error`. This allows you to catch all errors raised by the API in a single place, making the implementation of your tools easier.

Also, each error message provides as much details about the *source* of the error as possibe. Ist most cases, the original error message is enoug for direct display to the user.

Have a look at the following example code:

.. literalinclude:: examples/error_handling.py
    :language: python

Successful Run
==============

If you run this code with a valid configuration file, you will see the following output:

.. literalinclude:: examples/error_handling_1.elcl
    :language: erbsland-conf

.. code-block:: text

    Server name: host01.example.com
    Port: 9170
    Client 0: ('client01', '192.168.1.10', 9000, [])
    Client 1: ('client02', '192.168.1.11', 9100, ['tree', 'leaf', 'branch', 'flower'])
    Client 2: ('client03', '192.168.1.12', 9170, [])
    Success!

IO Errors
=========

In case the configuration file is not found or cannot be read, the following error message is displayed:

.. code-block:: text

    Error reading the configuration.
    Failed to open file, path=/examples/error_handling_X.elcl, system error=[Errno 2] No such file or directory: '/examples/error_handling_X.elcl'

As you can see, the error message provides the *source* of the error including the error message from the underlying system.

Syntax, Encoding and Character Errors
=====================================

If there is a problem *while* parsing the configuration file, for example, a user forgets to put the double quotes around the IP address.

.. code-block:: erbsland-conf
    :force:

    -*[ Client ]*----------------------------------------------------------------
    Name               : "client02"
    IP                 : 192.168.1.11
    Port               : 9100

You will see an error message like this:

.. code-block:: text

    Error reading the configuration.
    Expected a valid value but got something else, source=file:/examples/error_handling_3.elcl:[15:22], name-path=client[1].ip

You not only see the exact location of the error in the *source* field, but also the *name-path* of the element that caused the error. This makes it easy, especially in large configurations, to find the exact location of the error.

If you have long and complex paths to the configuration files, you can also customize the error output:

.. code-block:: python

    print(e.to_text(elcl.ErrorOutput.FILENAME_ONLY | elcl.ErrorOutput.USE_LINES))

This will split the error message into multiple lines and only show the filename, without the full path:

.. code-block:: text

    Error reading the configuration.
    Expected a valid value but got something else
        source: file:error_handling_3.elcl:[15:22]
        name-path: client[1].ip

Errors while Interpreting the Parsed Result
===========================================

Error handling is not limited to the parsing of the configuration file. The API is designed to provide useful error messages if you access and convert the values. For example, in our demo code, the server name (at ``main.server.name``) is required and must be a string.

If a user forgets to provide a server name, the following error message is displayed:

.. code-block:: text

    Error reading the configuration.
    Value not found
        name-path: main.server.name

This is enough information for many use cases and extra line of code is required.

We also use the :meth:`~erbsland.conf.Value.get_text` method to convert the value to a string. If the value is not a string, the following error message is displayed:

.. code-block:: text

    Error reading the configuration.
    Expected value of type Text, got Integer
        source: file:error_handling_4.elcl:[7:22]
        name-path: main.server.name

This is, again, sufficient for most use cases. A user gets what's expected and the exact location of the error.


Generating Error Messages
=========================

Generating error messages is part of the public API. This is useful, if you already have a catch all error handler in place and do custom type checking in the configuration.

The error classes have a uniform interface, where you have one positional and required parameter with the error message itself, and many keyword parameters to provide additional details.

.. code-block:: python

    # ...
    value_x = doc["main.x"]
    if x := value_x.as_int(default=None):
        print(f"x is int: {x}")
    elif x := value_x.as_text(default=None):
        print(f"x is text: {x}")
    else:
        raise elcl.ConfTypeMismatch(
            "Expected integer or text value",
            source=value_x.location,
            name_path=value_x.name_path
        )

Here we raise a :class:`~erbsland.conf.error.ConfTypeMismatch` error if the value is neither an integer nor a text. To provide additional details, we pass the location of the value and the name path of the value.


.. button-ref:: ../reference/index
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    API Reference →
