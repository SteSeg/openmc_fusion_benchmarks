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

# extensions.append("sphinx_multiversion")

# Optional: control which tags/branches to build
smv_tag_whitelist = r'^\d+\.\d+\.\d+$'  # Only tags like 0.1.0, 0.2.1, etc.
smv_remote_whitelist = r'^origin$'
smv_released_pattern = r'^tags/v\d+\.\d+$'   # Treat tags as "released"
# Output folder is just the branch/tag name
smv_outputdir_format = '{ref.name}'
#

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "github_url": "https://github.com/SteSeg/openmc_fusion_benchmarks",
    "show_nav_level": 2,
    "navigation_with_keys": True,
    "use_edit_page_button": True,
    "navbar_end": ["version-switcher", "theme-switcher"],
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
}

html_context = {
    "github_user": "SteSeg",
    "github_repo": "openmc_fusion_benchmarks",
    "github_version": "to_ghpages",
    "doc_path": "docs",
}

html_show_sourcelink = True

# Optional: add logo and favicon
html_logo = "_static/logo.svg"
# html_favicon = "_static/favicon.ico"

# Enable static file path
html_static_path = ["_static"]
