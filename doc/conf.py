#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# -- Project information -----------------------------------------------------
project = "Erbsland Configuration Language Parser for Python"
copyright = "2025, Tobias Erbsland - Erbsland DEV"
author = "Tobias Erbsland - Erbsland DEV"
release = "1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
    "sphinx_design",
    "sphinx_copybutton",
    "_ext.ansi",
    "sphinx.ext.intersphinx",
]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Intersphinx configuration -----------------------------------------------
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- Autodoc configuration ---------------------------------------------------
autodoc_member_order = "bysource"
add_module_names = False

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_template_path = ["_templates"]
html_css_files = ["custom.css", "ansi.css", "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"]
#html_context = {"banner": "This documentation is still under development."}

# -- Add the syntax highlighter ---------------------------------------------
def setup(app):
    from _ext.pygments_elcl import ErbslandConfigurationLanguage

    app.add_lexer("erbsland-conf", ErbslandConfigurationLanguage)
