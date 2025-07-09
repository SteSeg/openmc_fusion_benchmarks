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
# release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_nb",
    "sphinxcontrib.bibtex",
    "sphinx_multiversion",
]

templates_path = ['_templates']
bibtex_bibfiles = ["references.bib"]

# -- Options for Sphinx Multiversion ----------------------------------------
# https://sphinx-multiversion.readthedocs.io/en/latest/configuration.html

# Only build tags like 1.0.0, 0.2.1, etc.
smv_tag_whitelist = r'^v?\d+\.\d+\.\d+$'
# Only build the docs-dev branch
smv_branch_whitelist = r'^docs-dev$'
# Optional: treat tags as "released"
smv_released_pattern = r'^tags/v?\d+\.\d+\.\d+$'
# Optional: name subfolders after tag/branch
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
    "github_version": "docs-dev",
    "doc_path": "docs",
}

html_context.update({
    "current_version": "{{ smv_current_version }}",
})

html_show_sourcelink = True

# Optional: add logo and favicon
html_theme_options = {
    "logo": {
        "image_light": "_static/logo.svg",
        "image_dark": "_static/logo.svg",
    },
}

# Enable static file path
html_static_path = ["_static"]

html_css_files = [
    "custom.css",
]
