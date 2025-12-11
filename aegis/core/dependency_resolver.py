"""
Component dependency resolution for Aegis Stack.

This module handles dependency resolution, validation, and recommendations
for component selection during project generation.
"""

from .component_utils import extract_base_component_name
from .components import COMPONENTS


class DependencyResolver:
    """Handles component dependency resolution and validation."""

    @staticmethod
    def resolve_dependencies(selected_components: list[str]) -> list[str]:
        """
        Resolve all dependencies and return final component list.

        Args:
            selected_components: List of component names selected by user
                                (may include bracket syntax like database[sqlite])

        Returns:
            Complete list of components including dependencies

        Raises:
            ValueError: If any selected components are invalid
        """
        # Validate all components first
        errors = DependencyResolver.validate_components(selected_components)
        if errors:
            raise ValueError(f"Invalid components: {'; '.join(errors)}")

        resolved = set(selected_components)

        # Resolve hard dependencies recursively
        while True:
            before_size = len(resolved)
            for component_name in list(resolved):
                # Extract base name for lookup in COMPONENTS
                base_name = extract_base_component_name(component_name)
                if base_name not in COMPONENTS:
                    continue

                component = COMPONENTS[base_name]
                if component.requires:
                    resolved.update(component.requires)

            if len(resolved) == before_size:
                break  # No new dependencies added

        return sorted(resolved)

    @staticmethod
    def validate_components(components: list[str]) -> list[str]:
        """
        Validate component selection and return errors.

        Args:
            components: List of component names to validate
                       (may include bracket syntax like database[sqlite])

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Extract base names for conflict checking
        base_components = [extract_base_component_name(c) for c in components]

        for component in components:
            # Extract base name for lookup
            base_name = extract_base_component_name(component)
            if base_name not in COMPONENTS:
                errors.append(f"Unknown component: {base_name}")
                continue

            spec = COMPONENTS[base_name]

            # Check conflicts using base names
            if spec.conflicts:
                for conflict in spec.conflicts:
                    if conflict in base_components:
                        errors.append(
                            f"Component '{base_name}' conflicts with '{conflict}'"
                        )

        return errors

    @staticmethod
    def get_recommendations(selected_components: list[str]) -> list[str]:
        """
        Get recommended components based on selection.

        Args:
            selected_components: List of already selected components
                                (may include bracket syntax like database[sqlite])

        Returns:
            List of recommended component names not already selected
        """
        recommendations = set()
        base_selected = {extract_base_component_name(c) for c in selected_components}

        for component_name in selected_components:
            # Extract base name for lookup
            base_name = extract_base_component_name(component_name)
            if base_name not in COMPONENTS:
                continue

            component = COMPONENTS[base_name]
            if component.recommends:
                for rec in component.recommends:
                    if rec not in base_selected:
                        recommendations.add(rec)

        return sorted(recommendations)

    @staticmethod
    def get_missing_dependencies(selected_components: list[str]) -> list[str]:
        """
        Get dependencies that would be auto-added.

        Args:
            selected_components: List of user-selected components

        Returns:
            List of dependencies that would be automatically added
        """
        resolved = DependencyResolver.resolve_dependencies(selected_components)
        auto_added = set(resolved) - set(selected_components)
        return sorted(auto_added)
