..
    Copyright (c) 2026 Tobias Erbsland - Erbsland DEV. https://erbsland.dev
    SPDX-License-Identifier: Apache-2.0

.. index::
    single: Changelog
    single: Changes

*********
Changelog
*********

Version 1.0.10
==============

*   Update of the pinned GutHub workflows. No functional changes.

Version 1.0.9
=============

Bug Fixes
---------

*   Fixed an issue where includes always counted as nested includes, what triggered the include limit when
    glob patterns were used.

Maintenance
-----------

*   Updated the ``requirements-...`` with the latest versions for all development and documentation dependencies.
    This has no effect on this library, as the library itself has no external dependencies.

Version 1.0.8
=============

Bug Fixes
---------

*   Fixed an issue where defaults provided via ``doc.get_list("path", str, default=[])`` did not work correctly.

Build Infrastructure
--------------------

*   Hardened the GitHub workflows.
*   Added maintenance utilities with pre-commit checks.
*   Added security hashes to validate and track changes in all important build infrastructure files.
*   Pinned the documentation build requirements.
*   Updated the build dependencies to the latest versions.
