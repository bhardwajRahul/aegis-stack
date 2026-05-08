# Frontend Component

Build user interfaces entirely in Python using [Flet](https://flet.dev/) - no JavaScript required.

!!! info "Always Included"
    The frontend component is automatically included in all Aegis Stack projects.

## What You Get

- **Python-only development** - Same language for frontend and backend
- **Direct service integration** - Call Python functions instead of REST APIs
- **Cross-platform foundation** - Web, desktop, and mobile from same code
- **[Overseer](../overseer/index.md)** - Built-in health monitoring dashboard

## Quick Start

### Basic Dashboard

```python
# app/components/frontend/main.py
import flet as ft
from app.services.health_service import get_system_health

def create_frontend_app():
    async def main(page: ft.Page):
        page.title = "Dashboard"
        page.theme_mode = ft.ThemeMode.SYSTEM
        
        health_view = ft.Text("Loading...")
        
        async def refresh_health(e):
            health = await get_system_health()  # Direct Python call
            status = "🟢 Healthy" if health.healthy else "🔴 Unhealthy"
            health_view.value = f"Status: {status}"
            page.update()
        
        page.add(
            ft.Text("System Dashboard", size=24),
            ft.ElevatedButton("Refresh", on_click=refresh_health),
            health_view
        )
    
    return main
```

### Mount on FastAPI

```python
# app/integrations/main.py
import flet.fastapi as flet_fastapi
from app.components.frontend.main import create_frontend_app

flet_app = flet_fastapi.app(create_frontend_app())
app.mount("/dashboard", flet_app)
# Access at http://localhost:8000/dashboard
```


## Key Advantages

| Traditional Stack | Aegis Stack |
|-------------------|-------------|
| Python + JavaScript | Python only |
| REST API calls | Direct function calls |
| Separate build processes | Single container |
| Multiple services | Single application |

## Next Steps

- **[Overseer](../overseer/index.md)** - Built-in health monitoring dashboard
- **[Flet Documentation](https://flet.dev/docs/)** - Complete UI framework reference

---

## Controls Reference

All reusable controls live under `app/components/frontend/controls/` and are exported from `app.components.frontend.controls`.

---

### SectionCard

`controls/section_card.py`

An outlined card with a tinted header bar and a content body. Matches the visual treatment of `DataTable` and `ActivityFeed`: 1px `OUTLINE` border, `Theme.Components.CARD_RADIUS` corner radius, and a header row tinted at 5% `ON_SURFACE` opacity, separated from the body by a 1px bottom-only hairline.

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str \| ft.Control` | required | Pass a string for standard `SecondaryText` treatment, or any control for a custom/mutable header label |
| `body` | `ft.Control` | required | Content rendered inside the card |
| `actions` | `list[ft.Control] \| None` | `None` | Controls right-aligned in the header row (e.g. a toggle button) |
| `body_padding` | `int \| ft.Padding` | `0` | Inner padding around `body`; pass `0` when the body owns its own padding |
| `header_padding_v` | `int` | `6` | Vertical padding on the header row |
| `expand` | `bool` | `False` | Forwarded to both the outer container and inner column |

**Usage:**

```python
from app.components.frontend.controls import SectionCard
from app.components.frontend.controls.buttons import PulseButton

preview_toggle = PulseButton(
    on_click_callable=self._toggle_preview,
    text="Preview",
    variant="muted",
    compact=True,
)

body_card = SectionCard(
    title="Body",
    body=my_text_field,
    actions=[preview_toggle],
)
```

Use `SectionCard` whenever a titled section should feel like a peer of the dashboard's data tables. The body field in the blog editor is a canonical example: the card owns the visible frame, and the inner `ft.TextField` uses `borderless=True` so it blends in.

---

### ActionMenu and ActionMenuItem

`controls/action_menu.py`

Composable kebab row-action menu for data tables and lists.

**`ActionMenu(items: list[ft.PopupMenuItem])`**

Renders a `MORE_HORIZ` icon button (`ft.Colors.ON_SURFACE_VARIANT`) with tooltip "Actions". Wraps `ft.PopupMenuButton`.

**`ActionMenuItem(label, icon, on_click, *, destructive=False)`**

A `ft.PopupMenuItem` with an icon+label row. When `destructive=True`, both the icon and label render in `ft.Colors.ERROR` (red); otherwise the icon is `ON_SURFACE_VARIANT` and the label is `ON_SURFACE`.

Use a bare `ft.PopupMenuItem()` (no args) inside the items list to insert a divider between groups.

**Usage:**

```python
from app.components.frontend.controls import ActionMenu, ActionMenuItem
import flet as ft

def _build_row_actions(self, item_id: int) -> ft.Control:
    return ActionMenu([
        ActionMenuItem("Edit", ft.Icons.EDIT, lambda _: self._edit(item_id)),
        ActionMenuItem("Archive", ft.Icons.ARCHIVE, lambda _: self._archive(item_id)),
        ft.PopupMenuItem(),  # divider
        ActionMenuItem(
            "Delete",
            ft.Icons.DELETE_OUTLINE,
            lambda _: self._confirm_delete(item_id),
            destructive=True,
        ),
    ])
```

---

### PulseButton

`controls/buttons.py`

Flat, accent-tinted button. No drop shadow; visual weight comes from a 1px border and a translucent fill that deepens on hover.

**Variants:**

| Variant | Appearance | Use for |
|---------|-----------|---------|
| `"teal"` (default) | Teal border + fill | Primary / brand action |
| `"amber"` | Amber border + fill | Secondary or highlight |
| `"muted"` | Muted outline | Inactive toggles, Cancel |
| `"stop"` | Red border + 10% red fill | Destructive primary CTA |

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `on_click_callable` | `Callable` | required | Must be async (no-arg) |
| `text` | `str` | required | Button label |
| `variant` | `str` | `"teal"` | Color variant (see table above) |
| `compact` | `bool` | `False` | Dense mode: height 28 (vs 40), padding `symmetric(h=10, v=2)`, radius 6 |

**`set_variant(variant: str) -> None`**

Swaps the color variant at runtime while preserving `compact` mode. Used for toggle-style buttons where the label stays the same but the active state flips the color:

```python
# On toggle click
self._preview_btn.set_variant("teal" if is_preview else "muted")
```

**Usage:**

```python
from app.components.frontend.controls.buttons import PulseButton

# Standard CTA
save_btn = PulseButton(on_click_callable=self._save, text="Save")

# Compact, for card headers
toggle_btn = PulseButton(
    on_click_callable=self._toggle,
    text="Preview",
    variant="muted",
    compact=True,
)

# Destructive
delete_btn = PulseButton(
    on_click_callable=self._delete,
    text="Delete",
    variant="stop",
)
```

---

### ConfirmDialog

`controls/buttons.py`

Themed confirmation dialog with cancel, optional secondary, and confirm buttons. Inherits from `ft.AlertDialog`.

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `ft.Page` | required | |
| `title` | `str` | required | Dialog title |
| `message` | `str` | required | Body text |
| `confirm_text` | `str` | `"Confirm"` | Confirm button label |
| `cancel_text` | `str` | `"Cancel"` | Cancel button label |
| `on_confirm` | `Callable \| None` | `None` | Callback on confirm (sync or async) |
| `destructive` | `bool` | `False` | When True, confirm button uses `"stop"` variant (red) |
| `secondary_text` | `str \| None` | `None` | When set, renders a third button between Cancel and Confirm |
| `on_secondary` | `Callable \| None` | `None` | Callback for the secondary button (sync or async) |
| `secondary_destructive` | `bool` | `False` | When True, secondary button uses `"stop"` variant; otherwise muted |

Both `on_confirm` and `on_secondary` accept sync or async callables via a shared `_dispatch` helper.

**Two-action example** (simple delete confirmation):

```python
from app.components.frontend.controls.buttons import ConfirmDialog

def _confirm_delete(self, item_id: int) -> None:
    async def _do_delete() -> None:
        await self._delete(item_id)

    ConfirmDialog(
        page=self.page,
        title="Delete item?",
        message="This cannot be undone.",
        confirm_text="Delete",
        destructive=True,
        on_confirm=_do_delete,
    ).show()
```

**Three-action example** (unsaved changes prompt):

```python
ConfirmDialog(
    page=self.page,
    title="Unsaved changes",
    message="Save your edits as a draft, or discard them?",
    confirm_text="Save Draft",
    secondary_text="Discard",
    secondary_destructive=True,
    cancel_text="Cancel",
    on_confirm=_save_and_continue,
    on_secondary=_discard,
).show()
```

This renders: `[Cancel]  [Discard (red)]  [Save Draft (teal)]`

---

### FormTextField

`controls/form_fields.py`

Reusable text input with a label above and optional error text below. Theme-aware border radius and colors.

**Additional constructor parameters** (beyond the existing ones):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `show_label` | `bool` | `True` | When False, skips the label widget and the 4px gap above the field. Use when an outer container (e.g. a `SectionCard` header) already provides the label. |
| `borderless` | `bool` | `False` | When True, drops the border, corner radius, and fill so the field blends into a parent container that owns the visible frame. |

**`borderless` use case:** The blog editor's Body field sits inside a `SectionCard` that owns the visible border. Setting `borderless=True` on the inner `ft.TextField` makes the two-layer structure seamless.

**Usage:**

```python
from app.components.frontend.controls import FormTextField

# Standard labeled field
title = FormTextField(label="Title", width=360, on_change=self._on_title_change)

# No label (parent SectionCard provides the heading)
body = FormTextField(
    label="Body",
    show_label=False,
    borderless=True,
    multiline=True,
    min_lines=14,
)
```

---

### FormDropdown

`controls/form_fields.py`

Reusable dropdown that mirrors `FormTextField`'s layout: label above, field below, optional error line below that. Uses the same border radius, surface color, and focused border as the other form controls.

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `label` | `str` | required | Label text above the dropdown |
| `options` | `list[tuple[str, str]]` | required | List of `(key, display_label)` pairs; `key` is what `.value` returns |
| `value` | `str \| None` | first option's key | Initially selected key |
| `on_change` | `Callable \| None` | `None` | Fires when selection changes |
| `error` | `str \| None` | `None` | Error message below the field |
| `disabled` | `bool` | `False` | |
| `width` | `int \| None` | `None` | Fixed width; omit for `expand` |

**`.value`** returns the currently selected key (not the display label).

**Usage:**

```python
from app.components.frontend.controls import FormDropdown

status_filter = FormDropdown(
    label="Status",
    value="all",
    width=180,
    options=[
        ("all", "All"),
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ],
    on_change=lambda _: page.run_task(self._reload),
)

# Read current selection
selected = status_filter.value  # e.g. "draft"
```

The "all" sentinel shown above is a UI convention: the dropdown displays "All" but the caller checks `if value != "all"` before passing a status filter to the API.