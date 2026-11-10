
***************
Source Resolver
***************

The source resolver module contains all interfaces to implement a custom source resolver, that is used when a configuration contains ``@include`` meta-commands.

This implementation also provides a default implementation for a source resolver in the module :mod:`~erbsland.conf.file_source_resolver`. This desfault implementation is used by default, but you can customize it by creating you own instance.

Interface
=========

.. automodule:: erbsland.conf.source_resolver
    :members:

.. automodule:: erbsland.conf.file_source_resolver
    :members:

