"""
Reusable form field components for Aegis Stack dashboard.

Provides theme-aware form inputs with consistent styling for labels,
text fields, secret fields (with visibility toggle), and action buttons.

Variants:
- ``"default"`` — Material-themed inputs (current behavior).
- ``"pulse"`` — Pulse aesthetic: dark CARD bg, teal focus border, caps
  tracked label. Use this on Pulse-styled views like the login form.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

import flet as ft
from app.components.frontend.controls.buttons import (
    ElevatedCancelButton,
    ElevatedUpdateButton,
)
from app.components.frontend.controls.text import LabelText
from app.components.frontend.styles import PulseColors
from app.components.frontend.theme import AegisTheme as Theme

FormVariant = Literal["default", "pulse"]
_PULSE_LABEL_STYLE = ft.TextStyle(letter_spacing=1.6)


def _build_label(text: str, variant: FormVariant) -> ft.Control:
    """Pick the right label widget for the variant."""
    if variant == "pulse":
        return LabelText(
            text.upper(),
            color=PulseColors.MUTED,
            size=10,
            weight=ft.FontWeight.W_500,
            style=_PULSE_LABEL_STYLE,
        )
    return LabelText(text)


def _input_kwargs(variant: FormVariant, error: str | None) -> dict[str, Any]:
    """Per-variant ft.TextField kwargs (border, bg, text colors).

    Pulse variant matches the web frontend's
    ``border border-aegis-border rounded px-3 py-2 text-sm`` recipe —
    14px text, 12px horizontal padding, 4px corner radius. Height pinned
    to 40 so fields visually align with ``PulseButton``.
    """
    if variant == "pulse":
        return {
            "border_color": PulseColors.BORDER if not error else "#E94E77",
            "focused_border_color": PulseColors.TEAL,
            "cursor_color": PulseColors.TEAL,
            "bgcolor": PulseColors.CARD,
            "text_style": ft.TextStyle(color=PulseColors.TEXT, size=14),
            "hint_style": ft.TextStyle(color=PulseColors.MUTED, size=14),
            "border_radius": 4,
            "filled": True,
            "content_padding": ft.padding.symmetric(horizontal=12, vertical=10),
            "height": 40,
        }
    return {
        "border_radius": Theme.Components.INPUT_RADIUS,
        "bgcolor": ft.Colors.SURFACE,
        "border_color": Theme.Colors.ERROR if error else ft.Colors.OUTLINE,
        "focused_border_color": Theme.Colors.PRIMARY,
        "text_size": 13,
        "content_padding": ft.padding.symmetric(horizontal=12, vertical=10),
    }


class FormTextField(ft.Container):
    """
    Reusable text input with label and error state.

    Features:
    - Theme-aware styling with consistent border radius and colors
    - Label using existing LabelText component
    - Error text display below field (red) when error provided
    - Optional hint text for placeholder guidance
    """

    def __init__(
        self,
        label: str,
        value: str = "",
        hint: str = "",
        on_change: Callable[[ft.ControlEvent], None] | None = None,
        # Flet's TextField accepts both sync and async on_submit at runtime.
        on_submit: (
            Callable[[ft.ControlEvent], Awaitable[None] | None] | None
        ) = None,
        error: str | None = None,
        disabled: bool = False,
        width: int | None = None,
        variant: FormVariant = "default",
        keyboard_type: str | None = None,
        autofocus: bool = False,
        password: bool = False,
        can_reveal_password: bool = False,
    ) -> None:
        """
        Initialize form text field.

        Args:
            label: Label text displayed above the field
            value: Initial value for the field
            hint: Placeholder/hint text when field is empty
            on_change: Callback when field value changes
            on_submit: Callback when the user presses enter
            error: Error message to display below field (None = no error)
            disabled: Whether the field is disabled
            width: Optional fixed width for the field
            variant: Style variant (``"default"`` or ``"pulse"``)
            keyboard_type: Optional ``ft.KeyboardType`` (e.g. EMAIL)
            autofocus: Focus this field on mount
            password: Mask the value
            can_reveal_password: Add Flet's built-in reveal toggle
        """
        super().__init__()

        self._label = label
        self._error = error
        self._on_change = on_change
        self._variant = variant

        # Outer Container takes the explicit width so siblings (buttons,
        # dividers) can match it.
        if width is not None:
            self.width = width

        self._text_field = ft.TextField(
            value=value,
            hint_text=hint,
            on_change=self._handle_change,
            on_submit=on_submit,
            disabled=disabled,
            keyboard_type=keyboard_type,
            autofocus=autofocus,
            password=password,
            can_reveal_password=can_reveal_password,
            expand=width is None,
            width=width,
            **_input_kwargs(variant, error),
        )

        self._build_content()

    def _build_content(self) -> None:
        """Build the form field content with label and optional error."""
        children: list[ft.Control] = [
            _build_label(self._label, self._variant),
            ft.Container(height=4),
            self._text_field,
        ]

        if self._error:
            children.append(ft.Container(height=4))
            children.append(
                ft.Text(
                    self._error,
                    size=Theme.Typography.BODY_SMALL,
                    color=Theme.Colors.ERROR,
                )
            )

        self.content = ft.Column(children, spacing=0, tight=True)

    def _handle_change(self, e: ft.ControlEvent) -> None:
        """Handle text field change events."""
        if self._on_change:
            self._on_change(e)

    @property
    def value(self) -> str:
        """Get the current field value."""
        return self._text_field.value or ""

    @value.setter
    def value(self, new_value: str) -> None:
        """Set the field value."""
        self._text_field.value = new_value
        if self.page:
            self._text_field.update()

    def set_error(self, error: str | None) -> None:
        """Set or clear the error message."""
        self._error = error
        if self._variant == "pulse":
            self._text_field.border_color = "#E94E77" if error else PulseColors.BORDER
        else:
            self._text_field.border_color = (
                Theme.Colors.ERROR if error else ft.Colors.OUTLINE
            )
        self._build_content()
        if self.page:
            self.update()

    def focus(self) -> None:
        """Focus the text field."""
        self._text_field.focus()


class FormSecretField(ft.Container):
    """
    Text input for secrets with show/hide toggle.

    Features:
    - Password field with visibility toggle (eye icon)
    - Theme-aware styling consistent with FormTextField
    - Never shows full value in view mode (always masked)
    - Label and error state support
    """

    def __init__(
        self,
        label: str,
        value: str = "",
        hint: str = "Enter value...",
        on_change: Callable[[ft.ControlEvent], None] | None = None,
        error: str | None = None,
        disabled: bool = False,
        width: int | None = None,
    ) -> None:
        """
        Initialize form secret field.

        Args:
            label: Label text displayed above the field
            value: Initial value for the field
            hint: Placeholder/hint text when field is empty
            on_change: Callback when field value changes
            error: Error message to display below field (None = no error)
            disabled: Whether the field is disabled
            width: Optional fixed width for the field
        """
        super().__init__()

        self._label = label
        self._error = error
        self._on_change = on_change
        self._password_visible = False

        # Create the text field
        self._text_field = ft.TextField(
            value=value,
            hint_text=hint,
            password=True,
            can_reveal_password=False,  # We use our own toggle
            on_change=self._handle_change,
            disabled=disabled,
            border_radius=Theme.Components.INPUT_RADIUS,
            bgcolor=ft.Colors.SURFACE,
            border_color=Theme.Colors.ERROR if error else ft.Colors.OUTLINE,
            focused_border_color=Theme.Colors.PRIMARY,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            expand=True,
        )

        # Create visibility toggle button
        self._toggle_button = ft.IconButton(
            icon=ft.Icons.VISIBILITY_OFF,
            icon_color=Theme.Colors.TEXT_SECONDARY,
            icon_size=18,
            tooltip="Show/hide value",
            on_click=self._toggle_visibility,
            disabled=disabled,
        )

        # Build content
        self._build_content(width)

    def _build_content(self, width: int | None = None) -> None:
        """Build the form field content with label, field, toggle, and error."""
        # Field with toggle button
        field_row = ft.Row(
            [
                self._text_field,
                self._toggle_button,
            ],
            spacing=4,
            expand=width is None,
            width=width,
        )

        children: list[ft.Control] = [
            LabelText(self._label),
            ft.Container(height=4),
            field_row,
        ]

        # Add error text if present
        if self._error:
            children.append(ft.Container(height=4))
            children.append(
                ft.Text(
                    self._error,
                    size=Theme.Typography.BODY_SMALL,
                    color=Theme.Colors.ERROR,
                )
            )

        self.content = ft.Column(
            children,
            spacing=0,
            tight=True,
        )

    def _handle_change(self, e: ft.ControlEvent) -> None:
        """Handle text field change events."""
        if self._on_change:
            self._on_change(e)

    def _toggle_visibility(self, e: ft.ControlEvent) -> None:
        """Toggle password visibility."""
        self._password_visible = not self._password_visible
        self._text_field.password = not self._password_visible
        self._toggle_button.icon = (
            ft.Icons.VISIBILITY if self._password_visible else ft.Icons.VISIBILITY_OFF
        )
        if self.page:
            self._text_field.update()
            self._toggle_button.update()

    @property
    def value(self) -> str:
        """Get the current field value."""
        return self._text_field.value or ""

    @value.setter
    def value(self, new_value: str) -> None:
        """Set the field value."""
        self._text_field.value = new_value
        if self.page:
            self._text_field.update()

    def set_error(self, error: str | None) -> None:
        """Set or clear the error message."""
        self._error = error
        # Update border color based on error state
        self._text_field.border_color = (
            Theme.Colors.ERROR if error else ft.Colors.OUTLINE
        )
        self._build_content()
        if self.page:
            self.update()

    def focus(self) -> None:
        """Focus the text field."""
        self._text_field.focus()


class FormDropdown(ft.Container):
    """
    Reusable dropdown with label and error state.

    Mirrors ``FormTextField``'s shape (label above, field below, optional
    error line) so forms mixing text inputs and dropdowns stay visually
    consistent. Theme-aware styling: same border radius, surface colour,
    and focused border as the rest of the form controls.
    """

    def __init__(
        self,
        label: str,
        options: list[tuple[str, str]],
        value: str | None = None,
        on_change: Callable[[ft.ControlEvent], None] | None = None,
        error: str | None = None,
        disabled: bool = False,
        width: int | None = None,
    ) -> None:
        """
        Initialize form dropdown.

        Args:
            label: Label text displayed above the dropdown.
            options: List of (key, display_label) tuples. `key` is what
                ``value`` returns; `display_label` is what the user sees.
            value: Initial selected key. Defaults to the first option's key.
            on_change: Callback when selection changes.
            error: Error message to display below the dropdown.
            disabled: Whether the dropdown is disabled.
            width: Optional fixed width; omit for `expand`.
        """
        super().__init__()

        self._label = label
        self._error = error
        self._on_change = on_change

        initial = value if value is not None else (options[0][0] if options else None)

        self._dropdown = ft.Dropdown(
            value=initial,
            options=[ft.dropdown.Option(key=k, text=t) for k, t in options],
            on_change=self._handle_change,
            disabled=disabled,
            border_radius=Theme.Components.INPUT_RADIUS,
            bgcolor=ft.Colors.SURFACE,
            border_color=Theme.Colors.ERROR if error else ft.Colors.OUTLINE,
            focused_border_color=Theme.Colors.PRIMARY,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            expand=width is None,
            width=width,
        )

        self._build_content()

    def _build_content(self) -> None:
        """Build the dropdown content with label and optional error."""
        children: list[ft.Control] = [
            LabelText(self._label),
            ft.Container(height=4),
            self._dropdown,
        ]

        if self._error:
            children.append(ft.Container(height=4))
            children.append(
                ft.Text(
                    self._error,
                    size=Theme.Typography.BODY_SMALL,
                    color=Theme.Colors.ERROR,
                )
            )

        self.content = ft.Column(children, spacing=0, tight=True)

    def _handle_change(self, e: ft.ControlEvent) -> None:
        """Handle dropdown change events."""
        if self._on_change:
            self._on_change(e)

    @property
    def value(self) -> str:
        """Get the currently selected key."""
        return self._dropdown.value or ""

    @value.setter
    def value(self, new_value: str) -> None:
        """Set the selected key."""
        self._dropdown.value = new_value
        if self.page:
            self._dropdown.update()

    def set_error(self, error: str | None) -> None:
        """Set or clear the error message."""
        self._error = error
        self._dropdown.border_color = Theme.Colors.ERROR if error else ft.Colors.OUTLINE
        self._build_content()
        if self.page:
            self.update()


class FormActionButtons(ft.Row):
    """
    Save/Cancel button pair for forms.

    Features:
    - Uses existing ElevatedUpdateButton and ElevatedCancelButton
    - Shows loading state when saving=True
    - Consistent right-aligned layout
    """

    def __init__(
        self,
        on_save: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        save_text: str = "Save",
        cancel_text: str = "Cancel",
        saving: bool = False,
    ) -> None:
        """
        Initialize form action buttons.

        Args:
            on_save: Async callback when save button is clicked.
            on_cancel: Async callback when cancel button is clicked.
            save_text: Text for the save button.
            cancel_text: Text for the cancel button.
            saving: Whether save operation is in progress (shows loading).
        """
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._save_text = save_text
        self._saving = saving

        # Create buttons
        self._cancel_button = ElevatedCancelButton(
            on_click_callable=on_cancel,
            text=cancel_text,
        )

        self._save_button = ElevatedUpdateButton(
            on_click_callable=self._handle_save,
            text=save_text if not saving else "Saving...",
        )
        self._save_button.disabled = saving

        super().__init__(
            controls=[
                self._cancel_button,
                self._save_button,
            ],
            spacing=Theme.Spacing.SM,
            alignment=ft.MainAxisAlignment.END,
        )

    async def _handle_save(self) -> None:
        """Handle save button click."""
        await self._on_save()

    def set_saving(self, saving: bool) -> None:
        """Update the saving state."""
        self._saving = saving
        self._save_button.disabled = saving
        self._save_button.text = self._save_text if not saving else "Saving..."
        if self.page:
            self._save_button.update()
