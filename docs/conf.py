# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
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

jupyterlite_config = "docs/_jupyterlite"

exclude_patterns = [
    "_jupyterlite/**",
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
    "logo": {
        "image_light": "_static/logo.svg",
        "image_dark": "_static/logo.svg",
    },
    # https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/header-links.html#fontawesome-icons
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/SteSeg/openmc_fusion_benchmarks",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "Download PDF",
            "url": "_static/my_doc.pdf",
            "icon": "fa-solid fa-file-pdf",
            "attributes": {
                "download": None,
            }
        },
        {
            "name": "Fullscreen",
            "url": "#",
            "icon": "fa-solid fa-expand",
            "attributes": {
                "onclick": "document.documentElement.requestFullscreen()",
                "title": "Enter Fullscreen",
            }
        },
    ],
    "show_version_warning_banner": True,
    "icon_links_label": "Quick Links",
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["version-switcher", "icon-links", "theme-switcher"],
    "navbar_align": "content",
    "header_links_before_dropdown": 5,
    "use_edit_page_button": True,
    "navigation_with_keys": True,
    "analytics": {"google_analytics_id": "G-W1G68W77YV"},
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
    "default_mode": "light",
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

# html_show_sourcelink = True

# Enable static file path
html_static_path = ["_static"]
html_js_files = ["version-switcher.js"]

html_css_files = [
    "custom.css",
]
