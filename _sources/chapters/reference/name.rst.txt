
******************
Name and Name-Path
******************

Naming the individual elements in a configuration is done using name-paths. The API provides the classes :class:`NamePath<erbsland.conf.NamePath>` and :class:`Name<erbsland.conf.Name>` for this purpose.

The :class:`NamePath<erbsland.conf.NamePath>` has a built-in mini-parser, that parsers a string in the name-path format defined by the *Erbsland Configuration Language* into a :class:`NamePath<erbsland.conf.NamePath>` object. This parser also generates sytnax errors, like the configuraton parser does. It is a safe way to use name-paths in string format in your code.

Usage
=====

.. literalinclude:: examples/name.py
    :language: python

Interface
=========

.. autoclass:: erbsland.conf.Name
    :members:

.. autoclass:: erbsland.conf.NamePath
    :members:

