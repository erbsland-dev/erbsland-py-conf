#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from assignment_stream.as_helper import AsHelper


class TestAssignmentTextNames(AsHelper):

    def test_text_names(self):
        self.setup_from_file("text_name_values.elcl")
        self.require_section_map("text_names")
        self.require_value('text_names."One"', 1)
        self.require_value('text_names."  Two  "', 2)
        self.require_value('text_names."Good Morning!"', "おはようございます！")
        self.require_value('text_names."\\u{1f606}"', "😆")
        self.require_value('text_names."->\\u{1f606}"', "😆")
