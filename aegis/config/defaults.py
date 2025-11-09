"""
Default configuration values for Aegis Stack.

These values are derived from the aegis-stack pyproject.toml to maintain
a single source of truth.
"""

from pathlib import Path


def get_default_python_version() -> str:
    """
    Get default Python version from aegis-stack's pyproject.toml.

    Parses requires-python (e.g., ">=3.11,<3.14") and returns the minimum
    supported version (e.g., "3.11") for broader compatibility.

    Returns:
        Minimum supported Python version as string (e.g., "3.11")

    Note:
        Falls back to "3.11" if parsing fails to ensure graceful degradation.
    """
    try:
        # aegis-stack's pyproject.toml (not the template)
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

        if pyproject_path.exists():
            content = pyproject_path.read_text()

            for line in content.splitlines():
                if "requires-python" in line and ">=" in line:
                    # Parse: requires-python = ">=3.11,<3.14"
                    # Extract lower bound: >=3.11 → 3.11
                    lower_bound = line.split(">=")[1].split(",")[0].strip().strip('"')
                    return lower_bound
    except (FileNotFoundError, OSError, ValueError, IndexError):
        # Graceful fallback if parsing fails
        pass

    # Fallback default
    return "3.11"


# Single source of truth for default Python version
DEFAULT_PYTHON_VERSION = get_default_python_version()

# Supported Python versions (validated in CLI)
SUPPORTED_PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]
