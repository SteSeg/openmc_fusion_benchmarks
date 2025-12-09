# Configuration file for the Sphinx documentation builder.
# This file replaces jupyter-book build system

import os
import sys

# -- Project information -----------------------------------------------------
project = 'OpenMC Fusion Benchmarks'
copyright = '2025, OpenMC Fusion Benchmarks Contributors'
author = 'OpenMC Fusion Benchmarks Contributors'

# -- General configuration ---------------------------------------------------
extensions = [
    'myst_parser',
    'sphinxcontrib.bibtex',
]

# The master document (entry point)
master_doc = 'index'

# Bibliography files
bibtex_bibfiles = ['references.bib']
bibtex_reference_style = 'label'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '_config.yml', '_toc.yml']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_book_theme'
html_logo = 'images/logo.svg'
html_title = 'OpenMC Fusion Benchmarks'

html_theme_options = {
    'repository_url': 'https://github.com/eepeterson/openmc_fusion_benchmarks',
    'use_repository_button': True,
    'use_issues_button': True,
    'path_to_docs': 'docs/source',
    'repository_branch': 'develop',
}

# -- MyST options ------------------------------------------------------------
myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'dollarmath',
    'html_image',
]

# Allow HTML in Markdown
myst_html_meta = {
    "description lang=en": "OpenMC Fusion Benchmarks documentation",
}

# Don't execute notebooks (set to 'off' to disable)
# This is equivalent to jupyter-book's execute_notebooks: false
jupyter_execute_notebooks = 'off'
