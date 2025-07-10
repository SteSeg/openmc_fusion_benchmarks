"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------------
import datetime
import os
import sys

from pathlib import Path
from typing import Any, Dict

from sphinx.application import Sphinx
from sphinx.locale import _


sys.path.append(str(Path(".").resolve()))

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
    "_jupyterlite/**", "_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints",
]

templates_path = ['_templates']
bibtex_bibfiles = ["references.bib"]

intersphinx_mapping = {"sphinx": (
    "https://www.sphinx-doc.org/en/master", None)}

# -- MyST options ------------------------------------------------------------

# This allows us to use ::: to denote directives, useful for admonitions
myst_enable_extensions = ["colon_fence", "linkify", "substitution"]
myst_heading_anchors = 2
myst_substitutions = {"rtd": "[Read the Docs](https://readthedocs.org/)"}

# -- Internationalization ----------------------------------------------------

# specifying the natural language populates some key tags
language = "en"

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

# -- sphinx_ext_graphviz options ---------------------------------------------

graphviz_output_format = "svg"
inheritance_graph_attrs = dict(
    rankdir="LR",
    fontsize=14,
    ratio="compress",
)

# -- sphinx_togglebutton options ---------------------------------------------
togglebutton_hint = str(_("Click to expand"))
togglebutton_hint_hide = str(_("Click to collapse"))

# -- Sphinx-copybutton options ---------------------------------------------
# Exclude copy button from appearing over notebook cell numbers by using :not()
# The default copybutton selector is `div.highlight pre`
# https://github.com/executablebooks/sphinx-copybutton/blob/master/sphinx_copybutton/__init__.py#L82
copybutton_exclude = ".linenos, .gp"
copybutton_selector = ":not(.prompt) > div.highlight pre"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_logo = "_static/logo.svg"
html_favicon = "_static/logo.svg"
html_sourcelink_suffix = ""
html_last_updated_fmt = ""  # to reveal the build date in the pages meta

# Define the json_url for our version switcher.
json_url = "https://github.com/SteSeg/openmc_fusion_benchmarks/tree/docs-dev/docs/_static/version-switcher.json"

# Define the version we use for matching in the version switcher.
version_match = os.environ.get("READTHEDOCS_VERSION")
release = "9.9.9"
# If READTHEDOCS_VERSION doesn't exist, we're not on RTD
# If it is an integer, we're in a PR build and the version isn't correct.
# If it's "latest" → change to "dev" (that's what we want the switcher to call it)
if not version_match or version_match.isdigit() or version_match == "latest":
    # For local development, infer the version to match from the package.
    if "dev" in release or "rc" in release:
        version_match = "dev"
        # We want to keep the relative reference if we are in dev mode
        # but we want the whole url if we are effectively in a released version
        json_url = "_static/switcher.json"
    else:
        version_match = f"v{release}"
elif version_match == "stable":
    version_match = f"v{release}"

html_theme_options = {
    "header_links_before_dropdown": 5,
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
    "logo": {
        "text": "openfb",
        "image_light": "_static/logo.svg",
        "image_dark": "_static/logo.svg",
    },
    "use_edit_page_button": True,
    "show_toc_level": 1,
    "show_version_warning_banner": True,
    "icon_links_label": "Quick Links",
    "navbar_start": ["navbar-logo", "version-switcher"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["icon-links", "theme-switcher"],
    "navbar_align": "content",
    "navigation_with_keys": True,
    "analytics": {"google_analytics_id": "G-W1G68W77YV"},
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
    "secondary_sidebar_items": {
        # Keep default for all other pages
        "**": ["page-toc", "edit-this-page", "sourcelink"],
        "index": [],  # Disable on index
    },
    "switcher": {
        "json_url": json_url,
        "version_match": version_match,
    },
    # "back_to_top_button": False,
    "search_as_you_type": True,
}

html_context = {
    "github_user": "SteSeg",
    "github_repo": "openmc_fusion_benchmarks",
    "github_version": "docs-dev",
    "doc_path": "docs",
    "default_mode": "light",
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


# -- favicon options ---------------------------------------------------------

# see https://sphinx-favicon.readthedocs.io for more information about the
# sphinx-favicon extension
favicons = [
    # generic icons compatible with most browsers
    "favicon-32x32.png",
    "favicon-16x16.png",
    {"rel": "shortcut icon", "sizes": "any", "href": "favicon.ico"},
    # chrome specific
    "android-chrome-192x192.png",
    # apple icons
    {"rel": "mask-icon", "color": "#459db9", "href": "safari-pinned-tab.svg"},
    {"rel": "apple-touch-icon", "href": "apple-touch-icon.png"},
    # msapplications
    {"name": "msapplication-TileColor", "content": "#459db9"},
    {"name": "theme-color", "content": "#ffffff"},
    {"name": "msapplication-TileImage", "content": "mstile-150x150.png"},
]


# -- Options for autosummary/autodoc output ------------------------------------
autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "groupwise"

# -- Options for autoapi -------------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../src/pydata_sphinx_theme"]
autoapi_keep_files = True
autoapi_root = "api"
autoapi_member_order = "groupwise"


# -- Warnings / Nitpicky -------------------------------------------------------

nitpicky = True
bad_classes = (
    r".*abc def.*",  # urllib.parse.unquote_to_bytes
    r"api_sample\.RandomNumberGenerator",
    r"bs4\.BeautifulSoup",
    r"docutils\.nodes\.Node",
    r"matplotlib\.artist\.Artist",  # matplotlib xrefs are in the class diagram demo
    r"matplotlib\.figure\.Figure",
    r"matplotlib\.figure\.FigureBase",
    r"pygments\.formatters\.HtmlFormatter",
)
nitpick_ignore_regex = [
    *[("py:class", target) for target in bad_classes],
    # we demo some `urllib` docs on our site; don't care that its xrefs fail to resolve
    ("py:obj", r"urllib\.parse\.(Defrag|Parse|Split)Result(Bytes)?\.(count|index)"),
    # the kitchen sink pages include some intentional errors
    ("token", r"(suite|expression|target)"),
]


# -- application setup -------------------------------------------------------


def setup_to_main(
    app: Sphinx, pagename: str, templatename: str, context, doctree
) -> None:
    """
    Add a function that jinja can access for returning an "edit this page" link
    pointing to `main`.
    """

    def to_main(link: str) -> str:
        """
        Transform "edit on github" links and make sure they always point to the
        main branch.

        Args:
            link: the link to the github edit interface

        Returns:
            the link to the tip of the main branch for the same file
        """
        links = link.split("/")
        idx = links.index("edit")
        return "/".join(links[: idx + 1]) + "/main/" + "/".join(links[idx + 2:])

    context["to_main"] = to_main


def setup(app: Sphinx) -> Dict[str, Any]:
    """Add custom configuration to sphinx app.

    Args:
        app: the Sphinx application
    Returns:
        the 2 parallel parameters set to ``True``.
    """
    app.connect("html-page-context", setup_to_main)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
