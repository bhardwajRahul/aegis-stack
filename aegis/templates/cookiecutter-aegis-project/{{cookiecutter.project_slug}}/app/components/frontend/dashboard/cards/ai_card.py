"""
AI Service Card

Modern card component for displaying AI service status, provider configuration,
and conversation metrics in a clean 2-column layout.
"""

import flet as ft
from app.components.frontend.controls import LabelText, PrimaryText, ServiceCard
from app.components.frontend.controls.tech_badge import TechBadge
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    PROVIDER_COLORS,
    get_status_colors,
)


class AICard:
    """
    A clean AI service card with provider info and key metrics.

    Features:
    - Real AI service metrics from health checks
    - Clean 2-column layout (auth card pattern)
    - Provider-specific color coding
    - Highlighted metric containers
    - Config validation display
    - Responsive design
    """

    def __init__(self, component_data: ComponentStatus):
        """Initialize with AI service data from health check."""
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _get_provider_color(self, provider: str) -> str:
        """Get color for provider badge."""
        return PROVIDER_COLORS.get(provider.lower(), ft.Colors.GREY)

    def _truncate_model_name(self, model: str) -> str:
        """Intelligently truncate model name for display."""
        if not model:
            return "Unknown"

        # Keep it concise but recognizable
        if len(model) <= 20:
            return model

        # Handle common patterns
        if "claude" in model.lower():
            # "claude-3-5-sonnet-20241022" -> "claude-3.5-sonnet"
            parts = model.split("-")
            if len(parts) >= 4:
                return f"{parts[0]}-{parts[1]}.{parts[2]}-{parts[3]}"
        elif "llama" in model.lower():
            # "llama-3.1-70b-versatile" -> "llama-3.1-70b"
            parts = model.split("-")
            if len(parts) >= 3:
                return "-".join(parts[:3])
        elif "gpt" in model.lower():
            # "gpt-4-turbo-preview" -> "gpt-4-turbo"
            parts = model.split("-")
            if len(parts) >= 3:
                return "-".join(parts[:3])

        # Fallback: truncate with ellipsis
        return model[:20] + "..."

    def _create_metric_container(
        self, label: str, value: str, color: str = ft.Colors.BLUE
    ) -> ft.Container:
        """Create a properly sized metric container."""
        return ft.Container(
            content=ft.Column(
                [
                    LabelText(label),
                    ft.Container(height=8),  # Spacing
                    PrimaryText(value),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.all(16),
            bgcolor=ft.Colors.with_opacity(0.08, color),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, color)),
            height=80,  # Match auth card metric height
            expand=True,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create technology badge for AI service."""
        primary_color, _, _ = get_status_colors(self.component_data)

        # Infer engine from metadata (e.g., "pydantic-ai" or "langchain")
        engine = self.metadata.get("engine", "AI Engine")
        # Convert engine name to display format
        engine_display_map = {
            "pydantic-ai": "Pydantic AI",
            "langchain": "LangChain",
        }
        engine_display = engine_display_map.get(
            engine, engine.replace("-", " ").title() if engine else "AI Engine"
        )

        return TechBadge(
            title=engine_display,
            subtitle="AI Framework",
            badge_text="AI",
            badge_color=ft.Colors.CYAN,
            primary_color=primary_color,
        )

    def _get_config_status_display(self) -> tuple[str, str]:
        """
        Get config status display text and color.

        Returns:
            Tuple of (status_text, color)
        """
        config_valid = self.metadata.get("configuration_valid", False)
        validation_errors = self.metadata.get("validation_errors", [])

        if config_valid:
            return ("Valid", ft.Colors.GREEN)

        # Show specific error if only one
        if len(validation_errors) == 1:
            error_msg = validation_errors[0]
            if "api key" in error_msg.lower():
                return ("Missing API Key", ft.Colors.RED)
            elif "disabled" in error_msg.lower():
                return ("Disabled", ft.Colors.ORANGE)
            else:
                return ("Invalid", ft.Colors.RED)

        # Multiple errors
        if len(validation_errors) > 1:
            return (f"Issues ({len(validation_errors)})", ft.Colors.RED)

        # Shouldn't reach here, but just in case
        return ("Unknown", ft.Colors.GREY)

    def _get_response_time_color(self, response_time: float | None) -> str:
        """Get color for response time based on value."""
        if not response_time:
            return ft.Colors.GREY

        if response_time < 100:
            return ft.Colors.GREEN
        elif response_time < 500:
            return ft.Colors.ORANGE
        else:
            return ft.Colors.RED

    def _create_metrics_section(self) -> ft.Container:
        """Create the metrics section with a clean grid layout."""
        # Get real data from metadata
        provider = self.metadata.get("provider", "Unknown")
        model = self.metadata.get("model", "Unknown")
        total_conversations = self.metadata.get("total_conversations", 0)
        response_time = self.component_data.response_time_ms
        enabled = self.metadata.get("enabled", True)

        # Format values for display
        provider_display = provider.title()
        provider_color = self._get_provider_color(provider)
        model_display = self._truncate_model_name(model)
        conversations_display = str(total_conversations)
        supports_streaming = self.metadata.get("provider_supports_streaming", False)
        streaming_display = "Yes" if supports_streaming else "No"
        config_status, config_color = self._get_config_status_display()
        response_time_display = f"{response_time:.1f}ms" if response_time else "N/A"
        response_time_color = self._get_response_time_color(response_time)

        # If service disabled, show that prominently
        if not enabled:
            config_status = "Disabled"
            config_color = ft.Colors.RED

        # Create metrics grid (3 rows x 2 columns)
        return ft.Container(
            content=ft.Column(
                [
                    # Row 1: Provider and Model
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Provider", provider_display, provider_color
                            ),
                            self._create_metric_container(
                                "Model", model_display, ft.Colors.BLUE
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 2: Conversations and Streaming
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Conversations", conversations_display, ft.Colors.PURPLE
                            ),
                            self._create_metric_container(
                                "Streaming", streaming_display, ft.Colors.GREEN
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 3: Config Status and Response Time
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Config", config_status, config_color
                            ),
                            self._create_metric_container(
                                "Response Time",
                                response_time_display,
                                response_time_color,
                            ),
                        ],
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            expand=True,
            padding=ft.padding.all(16),
        )

    def build(self) -> ft.Container:
        """Build and return the complete AI service card."""
        # Get colors based on component status
        _, _, border_color = get_status_colors(self.component_data)

        # Use ServiceCard for consistent service card layout
        content = ServiceCard(
            left_content=self._create_technology_badge(),
            right_content=self._create_metrics_section(),
        )

        return CardContainer(
            content=content,
            border_color=border_color,
            component_data=self.component_data,
            component_name="ai",
        )
