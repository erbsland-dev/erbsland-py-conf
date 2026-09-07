*****
Usage
*****

The *Erbsland Configuration Language Parser* is designed to be simple to use out of the box.  
It comes with **sensible defaults** and a **flexible interface** that makes working with configuration values both straightforward and powerful.  

Here is a minimal example of loading a document and accessing a typed value:

.. code-block:: python

    import erbsland.conf as elcl

    # Load a configuration file
    doc = elcl.load("configuration.elcl")

    # Access a typed value with a fallback default
    port = doc.get_int("server.port", default=1234)

The goal of the library is to make parsing and accessing configuration values **as easy as possible**—with minimal boilerplate code and maximum clarity.

Let’s get started!

.. button-ref:: parsing
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Parsing a Document →

.. rubric:: No Time to Read?
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4

If you’d like to dive right in, here’s a **complete quick-start example**.
It demonstrates:

* Loading a configuration file
* Accessing required and optional values
* Iterating over sections and lists
* Using type-safe getters (``get_int``, ``get_text``, ``get_list``)
* Handling errors gracefully

.. literalinclude:: examples/quick-intro.py
    :language: python

This example expects a configuration file like the one below:

.. literalinclude:: examples/quick-intro.elcl
    :language: erbsland-conf

You can visualize the configuration above as the following tree:

.. literalinclude:: examples/quick-intro-tree.txt
    :language: text

.. rubric:: Need More Help?
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4

.. toctree::
    :maxdepth: 2

    parsing
    accessing_values
    working_with_types
    troubleshooting
    error_handling

