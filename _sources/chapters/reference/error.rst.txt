
*************
Error Classes
*************

This implementation provides individual error classes for all errors defined by the *Erbsland Configuration Language*. They all share a common base class :class:`~erbsland.conf.error.Error`, which allows a convenient "catch-all" error handling while parsing and evaluating the configuration.

The :class:`~erbsland.conf.error.ConfValueNotFound` error also subclasses :py:class:`KeyError`, to make value lookup match the usual Python conventions.


Interface
=========

.. automodule:: erbsland.conf.error
   :members: