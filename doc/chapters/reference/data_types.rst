
**********
Data Types
**********

In order to provide full compatibility with the *Erbsland Configuration Language*, this implementation provides a number of data types. The classes :class:`Time<erbsland.conf.Time>` and :class:`DateTime<erbsland.conf.DateTime>` extend the built-in :class:`datetime.time<python:datetime.time>` and :class:`datetime.datetime<python:datetime.datetime>` classes by adding nanosecond precision. The class :class:`TimeDelta<erbsland.conf.TimeDelta>` simply combines a count with a time unit and provides conversion to :class:`datetime.timedelta<python:datetime.timedelta>`, yet only for units that are supported by Python.


Interface
=========

.. autoclass:: erbsland.conf.Time
    :members:

.. autoclass:: erbsland.conf.DateTime
    :members:

.. autoclass:: erbsland.conf.TimeDelta
    :members:

