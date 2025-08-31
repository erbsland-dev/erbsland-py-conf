#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from assignment_stream.as_helper import AsHelper


class TestAssignmentSectionList(AsHelper):

    def test_section_lists(self):
        self.setup_from_file("section_lists.elcl")
        self.require_section_list("server")
        self.require_value("server.value", 1)
        self.require_section_list("server")
        self.require_value("server.value", 2)
        self.require_section_list("server")
        self.require_value("server.value", 3)
        self.require_section_list("client.config")
        self.require_value("client.config.value", 1)
        self.require_section_list("client.config")
        self.require_value("client.config.value", 2)
        self.require_section_list("client.config")
        self.require_value("client.config.value", 3)
