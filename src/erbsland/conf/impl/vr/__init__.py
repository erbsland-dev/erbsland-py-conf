# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0
"""
Compile and evaluate validation rules for both public authoring APIs.

The ELCL loader and Python builder produce mutable definitions in ``model``.
``compiler`` checks their structure and constraints, then ``relationships``
resolves schema references. The resulting immutable rules can be reused:
``validator`` owns all document mutations and state for one validation call,
while ``evaluation`` implements the local constraint predicates.
"""
