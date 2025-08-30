# scripts/gen_docs.py
"""
A script to dynamically generate documentation files for MkDocs.
This is run automatically by the mkdocs-gen-files plugin.
"""

import mkdocs_gen_files

print("--- Running gen_docs.py ---")

# Copy the root README.md to be the documentation's index page.
# This allows us to maintain a single source of truth for the project's
# main landing page, which is visible on both GitHub and the docs site.
with open("README.md") as readme:
    content = readme.read()

    # Fix paths for documentation context
    # Remove 'docs/' prefix from image paths (both light and dark versions)
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

    # Fix links to documentation pages (remove 'docs/' prefix)
    content = content.replace("](docs/cli-reference.md)", "](cli-reference.md)")
    content = content.replace("](docs/components/index.md)", "](components/index.md)")
    content = content.replace("](docs/philosophy.md)", "](philosophy.md)")

    # Use mkdocs_gen_files to create a virtual file instead of writing directly
    # This prevents triggering file change detection loops
    with mkdocs_gen_files.open("index.md", "w") as index:
        index.write(content)
        print("✓ Generated virtual index.md from README.md with fixed paths")
