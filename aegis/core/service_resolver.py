"""
Service dependency resolution for Aegis Stack.

This module handles service dependency resolution, converting service selections
to their required components and validating service-to-component compatibility.
"""

from ..constants import AnswerKeys, ComponentNames, StorageBackends
from .ai_service_parser import is_ai_service_with_options, parse_ai_service_config
from .component_utils import extract_base_service_name
from .dependency_resolver import DependencyResolver
from .services import SERVICES, get_service_dependencies


class ServiceResolver:
    """Handles service dependency resolution and validation."""

    @staticmethod
    def resolve_service_dependencies(
        selected_services: list[str],
    ) -> tuple[list[str], list[str]]:
        """
        Resolve services to their required components.

        Args:
            selected_services: List of service names selected by user
                              (may include bracket syntax like ai[sqlite])

        Returns:
            Tuple of (resolved_components, service_added_components)
            - resolved_components: All components needed (including auto-added)
            - service_added_components: Components that were added due to services

        Raises:
            ValueError: If any selected services are invalid
        """
        # Validate services first
        errors = ServiceResolver.validate_services(selected_services)
        if errors:
            raise ValueError(f"Invalid services: {'; '.join(errors)}")

        # Collect all components required by services
        service_required_components: set[str] = set()
        for service in selected_services:
            # Extract base service name (strip bracket info)
            base_service = extract_base_service_name(service)
            service_deps = get_service_dependencies(base_service)
            service_required_components.update(service_deps)

            # Handle AI service with persistence backend (from bracket syntax)
            if base_service == AnswerKeys.SERVICE_AI and is_ai_service_with_options(
                service
            ):
                ai_config = parse_ai_service_config(service)
                if ai_config.backend != StorageBackends.MEMORY:
                    # Auto-add database component for AI persistence
                    database_component = (
                        f"{ComponentNames.DATABASE}[{ai_config.backend}]"
                    )
                    service_required_components.add(database_component)

        # Convert to list and resolve component-to-component dependencies
        component_list = list(service_required_components)
        resolved_components = DependencyResolver.resolve_dependencies(component_list)

        # The service_added_components are what services directly require
        # (This represents what gets auto-added when services are selected)
        service_added_components = sorted(service_required_components)

        return resolved_components, service_added_components

    @staticmethod
    def validate_services(services: list[str]) -> list[str]:
        """
        Validate service selection and return errors.

        Args:
            services: List of service names to validate
                     (may include bracket syntax like ai[langchain, sqlite, openai])

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Extract base names for all services (strip bracket info)
        base_services = [extract_base_service_name(s) for s in services]

        for service in services:
            base_service = extract_base_service_name(service)
            if base_service not in SERVICES:
                errors.append(f"Unknown service: {base_service}")
                continue

            # Validate AI service bracket syntax if provided
            if base_service == AnswerKeys.SERVICE_AI and is_ai_service_with_options(
                service
            ):
                try:
                    ai_config = parse_ai_service_config(service)
                    valid_backends = [StorageBackends.MEMORY, StorageBackends.SQLITE]
                    if ai_config.backend not in valid_backends:
                        errors.append(
                            f"Invalid backend '{ai_config.backend}' for AI service. "
                            f"Valid options: {', '.join(valid_backends)}"
                        )
                except ValueError as e:
                    errors.append(f"Invalid AI service syntax: {e}")

            spec = SERVICES[base_service]

            # Check service conflicts
            if spec.conflicts:
                for conflict in spec.conflicts:
                    if conflict in base_services:
                        errors.append(
                            f"Service '{base_service}' conflicts with "
                            f"service '{conflict}'"
                        )

        # Check for service-to-service dependencies
        for service in services:
            base_service = extract_base_service_name(service)
            if base_service not in SERVICES:
                continue  # Already reported above

            spec = SERVICES[base_service]
            if spec.required_services:
                for required_service in spec.required_services:
                    if required_service not in base_services:
                        errors.append(
                            f"Service '{base_service}' requires "
                            f"service '{required_service}'"
                        )

        return errors

    @staticmethod
    def get_missing_components_for_services(
        selected_services: list[str], available_components: list[str]
    ) -> list[str]:
        """
        Get components that need to be added for the selected services.

        Args:
            selected_services: List of service names
            available_components: List of already available components

        Returns:
            List of component names that need to be added
        """
        if not selected_services:
            return []

        try:
            resolved_components, _ = ServiceResolver.resolve_service_dependencies(
                selected_services
            )
            missing = set(resolved_components) - set(available_components)
            return sorted(missing)
        except ValueError:
            # If services are invalid, return empty list
            return []

    @staticmethod
    def validate_service_component_compatibility(
        selected_services: list[str], available_components: list[str]
    ) -> list[str]:
        """
        Validate that all required components are available for selected services.

        Args:
            selected_services: List of service names
            available_components: List of available component names

        Returns:
            List of error messages (empty if compatible)
        """
        errors = []

        # First validate the services themselves
        service_errors = ServiceResolver.validate_services(selected_services)
        errors.extend(service_errors)

        # Then check component dependencies
        for service_name in selected_services:
            if service_name not in SERVICES:
                continue  # Already reported in service validation

            service_deps = get_service_dependencies(service_name)
            for required_comp in service_deps:
                if required_comp not in available_components:
                    errors.append(
                        f"Service '{service_name}' requires component '{required_comp}'"
                    )

        return errors

    @staticmethod
    def get_service_component_summary(
        selected_services: list[str],
    ) -> dict[str, list[str]]:
        """
        Get a summary of what components each service requires.

        Args:
            selected_services: List of service names

        Returns:
            Dictionary mapping service names to their required components
        """
        summary = {}

        for service_name in selected_services:
            if service_name in SERVICES:
                summary[service_name] = get_service_dependencies(service_name)
            else:
                summary[service_name] = []  # Unknown service

        return summary

    @staticmethod
    def recommend_components_for_services(selected_services: list[str]) -> list[str]:
        """
        Get recommended (but not required) components for selected services.

        Args:
            selected_services: List of service names

        Returns:
            List of recommended component names
        """
        recommendations = set()

        for service_name in selected_services:
            if service_name not in SERVICES:
                continue

            spec = SERVICES[service_name]
            if spec.recommended_components:
                recommendations.update(spec.recommended_components)

        return sorted(recommendations)

    @staticmethod
    def get_services_requiring_component(component_name: str) -> list[str]:
        """
        Get list of services that require a specific component.

        Args:
            component_name: Name of the component

        Returns:
            List of service names that require this component
        """
        requiring_services = []

        for service_name, spec in SERVICES.items():
            if component_name in spec.required_components:
                requiring_services.append(service_name)

        return requiring_services

    @staticmethod
    def merge_service_and_component_selections(
        selected_services: list[str], selected_components: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Merge service and component selections, resolving all dependencies.

        Args:
            selected_services: List of service names
            selected_components: List of component names

        Returns:
            Tuple of (final_components, auto_added_from_services, auto_added_from_components)
            - final_components: Final list of all components
            - auto_added_from_services: Components added due to service requirements
            - auto_added_from_components: Components added due to component dependencies

        Raises:
            ValueError: If services or components are invalid
        """
        # Resolve service dependencies first
        service_components, service_auto_added = (
            ServiceResolver.resolve_service_dependencies(selected_services)
        )

        # Combine with explicitly selected components
        all_components = list(set(selected_components + service_components))

        # Resolve final component dependencies
        final_components = DependencyResolver.resolve_dependencies(all_components)

        # Calculate what was auto-added from component dependencies
        component_auto_added = set(final_components) - set(all_components)

        return (
            final_components,
            sorted(service_auto_added),
            sorted(component_auto_added),
        )
