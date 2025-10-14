# scripts/gen_docs.py
"""
A script to dynamically generate documentation files for MkDocs.
This is run automatically by the mkdocs-gen-files plugin.
"""

import re

import mkdocs_gen_files

print("--- Running gen_docs.py ---")

# Copy the root README.md to be the documentation's index page.
# This allows us to maintain a single source of truth for the project's
# main landing page, which is visible on both GitHub and the docs site.
with open("README.md") as readme:
    content = readme.read()

    # Fix paths for documentation context
    # Convert single dark dashboard image to dual light/dark for MkDocs
    content = content.replace(
        "![System Health Dashboard](docs/images/dashboard-dark.png)",
        "![System Health Dashboard](images/dashboard-light.png#only-light)\n"
        "![System Health Dashboard](images/dashboard-dark.png#only-dark)",
    )
    # Handle existing light/dark syntax (remove docs/ prefix)
    content = content.replace(
        "![System Health Dashboard](docs/images/dashboard-light.png#only-light)",
        "![System Health Dashboard](images/dashboard-light.png#only-light)",
    )
    content = content.replace(
        "![System Health Dashboard](docs/images/dashboard-dark.png#only-dark)",
        "![System Health Dashboard](images/dashboard-dark.png#only-dark)",
    )
    # Handle legacy single image if it exists
    content = content.replace(
        "![System Health Dashboard](docs/images/dashboard.png)",
        "![System Health Dashboard](images/dashboard.png)",
    )
    # Fix Ron Swanson GIF path
    content = content.replace(
        "![Ron Swanson](docs/images/ron-swanson.gif)",
        "![Ron Swanson](images/ron-swanson.gif)",
    )
    # Fix CLI health check image path
    content = content.replace(
        "![CLI Health Check](docs/images/cli_health_check.png)",
        "![CLI Health Check](images/cli_health_check.png)",
    )
    # Convert GitHub picture element to MkDocs light/dark syntax
    picture_element = (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" '
        'srcset="docs/images/aegis-manifesto-dark.png">\n'
        '  <img src="docs/images/aegis-manifesto.png" alt="Aegis Stack" width="400">\n'
        "</picture>"
    )

    mkdocs_syntax = (
        '<img src="images/aegis-manifesto.png#only-light" '
        'alt="Aegis Stack" width="400">\n'
        '<img src="images/aegis-manifesto-dark.png#only-dark" '
        'alt="Aegis Stack" width="400">'
    )

    content = content.replace(picture_element, mkdocs_syntax)

    # Fallback: Fix standalone manifesto image paths
    content = content.replace(
        '<img src="docs/images/aegis-manifesto.png"',
        '<img src="images/aegis-manifesto.png"',
    )
    content = content.replace(
        '<img src="docs/images/aegis-manifesto-dark.png"',
        '<img src="images/aegis-manifesto-dark.png"',
    )

    # Fix links to documentation pages (remove 'docs/' prefix)
    # Use regex to catch all docs/*.md links instead of manually listing each one
    content = re.sub(r"\]\(docs/([^)]+\.md)\)", r"](\1)", content)

    # Use mkdocs_gen_files to create a virtual file instead of writing directly
    # This prevents triggering file change detection loops
    with mkdocs_gen_files.open("index.md", "w") as index:
        index.write(content)
        print("✓ Generated virtual index.md from README.md with fixed paths")
