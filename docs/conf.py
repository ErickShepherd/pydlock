# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pathlib
import re
import sys

# Make the package importable for autodoc without installing it.
_repo_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))

# -- Project information ------------------------------------------------------

project   = "pydlock"
author    = "Erick Edward Shepherd"
copyright = "2020-2026, Erick Edward Shepherd"

# Single-source the version from the package constants without importing the
# package (cryptography is not installed in the docs build).
_constants = (_repo_root / "pydlock" / "constants.py").read_text(encoding="utf-8")
release = re.search(r'__version__\s*=\s*"([^"]+)"', _constants).group(1)
version = release

# -- General configuration ----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

# cryptography is mocked so the docs build needs no compiled dependencies;
# autodoc only imports the package to read its docstrings.
autodoc_mock_imports = ["cryptography"]

autodoc_member_order = "bysource"
autodoc_typehints    = "description"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

templates_path   = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "audits",
    "design",
    "plans",
    "release-checklist.md",
]

# -- HTML output --------------------------------------------------------------

html_theme = "furo"
html_title = f"pydlock {release}"
html_static_path = ["_static"]
html_theme_options = {
    # Brand mark in the sidebar — black on light theme, white on dark.
    "light_logo": "pydlock-mark-black.png",
    "dark_logo": "pydlock-mark-white.png",
    # Backlink to the author's site in the page footer.
    "footer_icons": [
        {
            "name": "erickshepherd.com",
            "url": "https://erickshepherd.com",
            "html": "erickshepherd.com",
            "class": "",
        },
    ],
}
