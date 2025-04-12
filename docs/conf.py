# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = "Club Portal"
copyright = "2025, UF Computing Student Union"
author = "Isaac Hunter, Steve Sajeev, Lucas Romero-Wyhnanskyj, Jonathan Hooth"
github_url = "https://github.com/UF-CSU/club-portal-backend"

# The full version, including alpha/beta/rc tags
release = "1.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["myst_parser"]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

# Build in themes: https://www.sphinx-doc.org/en/master/usage/theming.html#builtin-themes
# 3rd Party Themes: https://sphinx-themes.org/
# Read the Docs Theme: https://sphinx-rtd-theme.readthedocs.io/en/latest/
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

myst_heading_anchors = 3
