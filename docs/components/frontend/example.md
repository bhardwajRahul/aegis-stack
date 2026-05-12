# Example

A small `BaseView` end to end. Adapted from `project_list_view.py` so it
matches what an Aegis project actually ships.

The view lists projects from the backend, renders a "Loading..." placeholder
on entry, replaces it with rows when the API call returns, and reloads the
same way whether the user just navigated in (`on_enter`) or just refreshed
the browser (`on_refresh`).

```python
# app/components/frontend/projects/project_list_view.py
from __future__ import annotations

from typing import Any

import flet as ft

from app.components.frontend.controls.section_card import SectionCard
from app.components.frontend.controls.text import BodyText, DisplayText
from app.components.frontend.controls.views.base import BaseView
from app.components.frontend.state.session_state import get_session_state


class ProjectListView(BaseView):
    def __init__(self, *, page: ft.Page, route: str) -> None:
        super().__init__(page=page, route=route, scroll=ft.ScrollMode.AUTO)

        self._body = ft.Column(
            controls=[BodyText("Loading...")],
            spacing=12,
            tight=True,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        DisplayText("Projects"),
                        SectionCard(
                            title="Owned projects",
                            body=self._body,
                            body_padding=16,
                        ),
                    ],
                    spacing=12,
                ),
                padding=24,
            ),
        ]

    async def on_enter(self, params: dict[str, Any]) -> None:
        await self._reload()

    async def on_refresh(self) -> None:
        await self._reload()

    async def _reload(self) -> None:
        api = get_session_state(self.page).api_client
        result = await api.get("/api/v1/insights/projects")
        if not isinstance(result, list):
            self._body.controls = [BodyText("Could not load projects.")]
            self._body.update()
            return
        self._body.controls = [BodyText(p.get("name", p["slug"])) for p in result]
        self._body.update()
```

And the registration that wires the route to the view, called once at
bootstrap from `app/components/frontend/main.py`:

```python
from app.components.frontend.core.routing import register_route
from app.components.frontend.core.routes import PROJECTS_ROUTE
from app.components.frontend.projects.project_list_view import ProjectListView

register_route(PROJECTS_ROUTE, ProjectListView)
```

## What this view does and does not do

It does not own its HTTP client. `get_session_state(self.page).api_client`
returns the per-session [`APIClient`](api-client.md) that the bootstrap
constructed. The same client carries the auth cookie that the user signed
in with, so the `/api/v1/insights/projects` call is authenticated without
any code in this view caring about tokens.

It does not own its theme. The colors, padding, and typography come from
the reusable controls under `app/components/frontend/controls/`:
`DisplayText`, `BodyText`, `SectionCard`. Those controls read from
`SessionState.theme_manager`.

It does not have an `on_leave`. There are no tasks to cancel; the data
load is a single `await` that resolves before the next user interaction.
If this view grew a `page.run_task` poll loop, the moment that handle
landed on `self`, `on_leave` would owe it a `cancel()`.

`on_enter` and `on_refresh` both delegate to `_reload`. This is the
canonical Aegis shape: the entry path and the browser-refresh path do
the same thing, factored into one private method.

## Where to go from here

The shipped views under `app/components/frontend/` are useful references
once the basics click:

- `app/components/frontend/projects/project_list_view.py` is the full
  version of the view above, with create/edit/delete affordances.
- `app/components/frontend/auth/login_view.py` shows a form view: holding
  references to inputs, validating, and calling `api.post_form`.
- `app/components/frontend/dashboard/` is the larger pattern: a view
  composed from many cards, each constructed by `CardFactory` based on
  which services are enabled in the project.

