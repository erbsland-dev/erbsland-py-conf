***************
Troubleshooting
***************

During development, this parser provides a few **diagnostic tools** that can help you understand how your configuration is being parsed and interpreted.  
These tools are especially useful when you are debugging configuration issues or verifying new features.  

Displaying the Parsed Document as a Value Tree
==============================================

Sometimes it’s useful to see the entire document as a **value tree**.  
You can do this for the whole document or for a specific section using the :meth:`~erbsland.conf.Value.to_test_value_tree` method.

.. literalinclude:: examples/troubleshooting_1.py
    :language: python

Running this example will produce output like the following:  

.. literalinclude:: examples/troubleshooting_1.txt
    :language: text

In this display:  

* The **left side** shows the hierarchical tree of names and sections.  
* The **right side** shows the parsed value assigned to each entry.  

This view is very handy for confirming that your configuration is parsed into the structure you expect.  
You can also adjust the formatting with flags from :class:`~erbsland.conf.TestOutput` to match your debugging needs.

Retrieving All Values as a Flat Dictionary
==========================================

Another way to inspect the parsed document is by converting it into a **flat dictionary** of key-value pairs.  
This can be done using the :meth:`~erbsland.conf.Document.to_flat_dict` method (available only on the root document).  

.. literalinclude:: examples/troubleshooting_2.py
    :language: python

Running this code produces output like the following:  

.. literalinclude:: examples/troubleshooting_2.txt
    :language: text

This representation is especially useful if you want a **quick overview** of all resolved values without navigating the hierarchy.

.. button-ref:: error_handling
    :ref-type: doc
    :color: success
    :class: sd-fs-5 sd-font-weight-bolder sd-my-4
    :expand:

    Error Handling →

