
************************
Working with Value Types
************************

The *Erbsland Configuration Language* supports several value types that can be used in configuration files.
The :class:`~erbsland.conf.Value` API provides convenient methods to automatically **validate** and **convert** these values into native Python types.

Two families of methods are available:

* ``as_...`` methods – validate and convert a value you already have.
* ``get_...`` methods – perform the lookup *and* convert the value in one step.

In general, we recommend using the ``get_...`` methods because they are more efficient and concise.
But let’s start by looking at the simpler ``as_...`` methods.

Converting a Value with ``as_...`` Methods
==========================================

If you already have a :class:`~erbsland.conf.Value` instance, you can call one of the ``as_...`` methods to check its type and convert it into the desired Python type.

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

In the example above:

* ``server.port`` is validated to be an integer and returned as a Python ``int``.
* ``server.host`` is validated to be text and returned as a Python ``str``.

Since no default values are provided, the ``as_...`` methods will raise a :class:`~erbsland.conf.error.ConfTypeMismatch` exception if the type is not as expected.
This exception clearly reports what type was required and what type was actually found, helping you quickly diagnose configuration errors.

Providing a Default Value
-------------------------

When you provide a default value, the ``as_...`` methods will return this default
if the actual value cannot be converted to the requested type—instead of raising an exception.

.. code-block:: python

    server_port = doc["server.port"].as_int(default=8080)
    server_host = doc["server.host"].as_text(default="localhost")

This allows for optional configuration values, that can be omitted from the configuration file.

Defaults can also be combined with ``None`` when you want to branch logic depending on the type:

.. code-block:: python

    value_x = doc["main.x"]

    if x := value_x.as_int(default=None):
        print(f"x is int: {x}")
    elif x := value_x.as_text(default=None):
        print(f"x is text: {x}")
    else:
        raise ConfTypeMismatch(
            "Expected integer or text value",
            source=value_x.location,
            name_path=value_x.name_path
        )

This way, the configuration can accept multiple types for the same value,
and you can handle each case explicitly.

Get Validated Lists
-------------------

The :meth:`~erbsland.conf.Value.as_list` method validates and converts list values.

.. code-block:: python

    int_list = doc["main.ports"].as_list(int)
    str_list = doc["main.names"].as_list(str)

How it works:

* Each element in the configuration is checked against the required type.
* The method returns a regular Python list of those native values.
* If the value is not a list but a single matching item, you’ll still get a list with one element.

This makes it easy to write code that always expects a list, regardless of how the configuration is written.

Using Dynamic Typing
--------------------

The :meth:`~erbsland.conf.Value.as_type` method provides a **dynamic alternative**.
It takes a Python type as a parameter and validates/returns the value as that type.

All ``as_<type>`` methods are basically shortcuts for ``as_type``,
but ``as_type`` becomes especially useful when you want to **link types dynamically** across multiple values.

.. code-block:: python

    tag_value = doc["main.tag"]

    if tag_value.type in [elcl.ValueType.TEXT, elcl.ValueType.INTEGER]:
        tag = tag_value.native()
        tag2 = doc["main.tag2"].as_type(type(tag))
        tag3 = doc["main.tag3"].as_type(type(tag))

Here:

* ``tag`` may be either a string or an integer.
* ``tag2`` and ``tag3`` are then validated to match the same type as ``tag``.

This approach is helpful when your configuration allows flexible typing,
but you still want to ensure internal consistency.


Combined Value Lookup and Conversion with ``get_...`` Methods
=============================================================

Instead of **looking up a value first** and then converting it,
it’s often easier and more efficient to use the ``get_...`` methods,
which do both steps in one go:

.. code-block:: python

    server_port = doc.get_int("server.port")
    server_host = doc.get_text("server.host")

Just like the ``as_...`` methods, the ``get_...`` methods validate the type
and raise an exception if the value does not match.

You can also provide default values for optional configuration values:

.. code-block:: python

    port = doc.get_int("server.port", default=8080)
    host = doc.get_text("server.host", default="localhost")

For lists, there is also a ``get_list`` method that performs type validation:

.. code-block:: python

    keywords = doc.get_list("filter.keywords", str)

This makes ``get_...`` methods the **preferred choice** in most real-world usage.

Relaxed Conversion
==================

Sometimes you don’t need strict type checking—you just want a value converted,
as long as it makes sense.

For these cases, use the :meth:`~erbsland.conf.Value.convert_to` method:

.. code-block:: python

    text = doc["main.value"].convert_to(str)

This method tries a **best effort conversion** to the requested type.

* If the conversion succeeds, you get the converted value.
* If the conversion fails, you still get a **default value of the requested type**.

This way, you are guaranteed to always receive a value of the requested type,
even if the configuration doesn’t match perfectly.

Manual Type Checks
==================

As a last resort, you can always inspect the raw type of a value.

.. code-block:: python

    value = doc["main.mystery"]

    if value.type in [elcl.ValueType.TEXT, elcl.ValueType.INTEGER, elcl.ValueType.FLOAT]:
        # handle value accordingly

This approach gives you full control, but usually the ``as_...`` or ``get_...`` methods
are cleaner and less error-prone. Use manual checks only when your logic
depends on multiple possible types in a flexible way.


.. button-ref:: troubleshooting
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Troubleshooting →

