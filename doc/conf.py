#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# -- Project information -----------------------------------------------------
project = "Erbsland Configuration Language Parser for Python"
copyright = f"{date.today().year}, Tobias Erbsland - Erbsland DEV"
author = "Tobias Erbsland - Erbsland DEV"
release = "1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
    "sphinx_design",
    "sphinx_copybutton",
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
html_css_files = ["custom.css"]
html_js_files = ["https://erbsland.dev/ext/fa7/js/all.min.js"]
#html_context = {"banner": "This documentation is still under development."}
