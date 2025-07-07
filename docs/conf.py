# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'openmc_fusion_benchmarks'
copyright = f"{datetime.datetime.now().year}, MIT PSFC Neutronics Team"
author = 'MIT PSFC Neutronics Team'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_nb",
    "sphinxcontrib.bibtex",
]

templates_path = ['_templates']
bibtex_bibfiles = ["references.bib"]

# -- Options for Sphinx Multiversion ----------------------------------------
# https://sphinx-multiversion.readthedocs.io/en/latest/configuration.html

extensions.append("sphinx_multiversion")

# Optional: control which tags/branches to build
smv_tag_whitelist = r'^\d+\.\d+\.\d+$'  # Only tags like 0.1.0, 0.2.1, etc.
smv_branch_whitelist = r'^.*$'  # Branches to include - all for the moment
smv_remote_whitelist = r'^origin$'
smv_released_pattern = r'^tags/v\d+\.\d+$'   # Treat tags as "released"
# Output folder is just the branch/tag name
smv_outputdir_format = '{ref.name}'
#

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"

html_theme_options = {
    "repository_url": "https://github.com/SteSeg/openmc_fusion_benchmarks",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "use_fullscreen_button": True,
    "switcher": True,
    "path_to_docs": "docs",  # Path from root to docs folder
}

# Optional: add logo and favicon
html_logo = "_static/logo.svg"
# html_favicon = "_static/favicon.ico"

# Enable static file path
html_static_path = ["_static"]
