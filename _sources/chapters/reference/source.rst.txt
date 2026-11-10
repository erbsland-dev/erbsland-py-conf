
*******
Sources
*******

In order to keep the parser extensible, input sources are represented as :class:`Source<erbsland.conf.Source>` objects. That way, the parser can work with any kind of input that adheres to this interface.

This implementation provides two source implementations, one for strings and one for files. Both implementations are considered internal and are only accessible through the parser interface.

Interface
=========

.. autoclass:: erbsland.conf.Source
   :members:

.. autoclass:: erbsland.conf.SourceIdentifier
   :members:

