# Installation Guide

Aegis Stack can be used in multiple ways depending on your needs and preferences.

## Installation

Choose the method that works best for your workflow:

=== "uvx (Recommended)"

    The fastest way to use Aegis Stack without any installation:

    ```bash
    # Create a new project
    uvx aegis-stack init my-project

    # Get help
    uvx aegis-stack --help

    # Create with specific components
    uvx aegis-stack init my-api --components worker,scheduler
    ```

    **Benefits:**

    - No installation required
    - Always uses latest version
    - Zero setup, works immediately
    - Isolated execution environment
    - Perfect for trying Aegis Stack or one-off usage

    **Best for:** Quick start, experimentation, CI/CD, one-off usage

=== "uv tool"

    Install Aegis Stack as a persistent CLI tool with uv:

    ```bash
    # Install persistently
    uv tool install aegis-stack

    # Use the installed version
    aegis init my-project
    aegis --help
    aegis components
    ```

    **Benefits:**

    - Fastest subsequent runs (pre-installed)
    - Simple `aegis` command
    - Easy to upgrade with `uv tool upgrade aegis-stack`
    - Persistent installation

    **Best for:** Daily development work, regular CLI usage

=== "pip"

    Install Aegis Stack with pip:

    ```bash
    # Install from PyPI
    pip install aegis-stack

    # Use the installed version
    aegis init my-project
    aegis --help
    aegis components
    ```

    **Benefits:**

    - Works in any Python environment
    - Familiar to all Python developers
    - Compatible with existing workflows

    **Best for:** Traditional workflows, existing pip-based setups

=== "Development"

    For contributing, customizing, or working with the latest development version:

    ```bash
    # Clone the repository
    git clone https://github.com/lbedner/aegis-stack
    cd aegis-stack

    # Install with all development dependencies
    uv sync --all-extras

    # Use development version
    .venv/bin/aegis init my-project

    # Run tests
    .venv/bin/pytest

    # Build documentation
    .venv/bin/mkdocs serve
    ```

    **Benefits:**

    - Latest unreleased features
    - Full development environment
    - Ability to modify and test changes
    - Access to development tools

    **Best for:** Contributing, customizing, latest features
