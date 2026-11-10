
************
Access Check
************

The :mod:`~erbsland.conf.access_check` module provides the interface for implementing access checks to configuration documents.

There is also a default implementation provided you find in the :mod:`~erbsland.conf.file_access_check` module. This implementation is used by default, but you can customize it by creating a own instance and passing it to the parser.

Usage
=====

Use the Default Implementation with Flags
-----------------------------------------

You can customize access to configuration files by creating a own instance of :class:`~erbsland.conf.file_access_check.FileAccessCheck` and passing it to the parser.

.. literalinclude:: examples/access_check_1.py
   :language: python

Create your Custom Access Check
-------------------------------

If you need custom logic to check access to configuration files, you can create your own implementation of :class:`~erbsland.conf.access_check.AccessCheck`. Only the method :meth:`~erbsland.conf.access_check.AccessCheck.check` needs to be implemented.

Return :data:`~erbsland.conf.access_check.AccessCheckResult.GRANTED` if access is granted, :data:`~erbsland.conf.access_check.AccessCheckResult.DENIED` otherwise. Alternatively you can raise an :class:`~erbsland.conf.error.ConfAccessError` if access is denied. If you raise an exception, the parser will automatically add the location of the include statement to the error message.

.. literalinclude:: examples/access_check_2.py
   :language: python

Interface
=========

.. automodule:: erbsland.conf.access_check
    :members:

.. automodule:: erbsland.conf.file_access_check
    :members:
