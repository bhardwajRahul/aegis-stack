# Templates and Partials

## The base layout

Every page extends `templates/base.html`, which owns the document skeleton and
exposes these blocks:

| Block | Use |
|---|---|
| `title` | Browser tab title. Defaults to the project name. |
| `favicon` | Override to swap the shipped SVG favicon. |
| `head_extra` | Per-page head additions: meta description, OG tags. |
| `navbar` | Replace the default bar (the landing does). |
| `page_body` | The whole `<main>` wrapper. Rarely overridden. |
| `content` | The page body. The block you normally use. |
| `footer` | Empty by default. |
| `scripts` | Per-page scripts, loaded after `app.js`. |

Override `content` for an ordinary page. Reach for `page_body` only when a
page needs to replace the entire main wrapper (the auth pages do, for their
split-screen shell).

The base loads htmx and Alpine from pinned CDN URLs. The Alpine *collapse
plugin* is loaded before Alpine core, deliberately: Alpine registers plugin
directives at init, so loading core first leaves `x-collapse` silently dead.

## Pages vs partials

The convention that keeps htmx code navigable:

- **`routes/pages.py`** holds full-page GETs. One handler per page; build the
  context, hand it to a template under `templates/pages/`.
- **`routes/partials/`** holds fragment routes. A partial backs an
  `hx-get`/`hx-post` on some element, returns an HTML fragment, and htmx swaps
  it into the DOM. Mount them under a `/partials/...` prefix in
  `create_web_frontend_app()`.

A useful test for which side something belongs on: if the browser URL should
change, it is a page; if an element on the current page should update, it is a
partial.

## Your first partial

A complete worked example: a button that fetches the current component health
and swaps it into the page without a reload.

1. The fragment template. Fragments have no `{% extends %}`; they are just
   the HTML that will be swapped in:

    ```html
    <!-- templates/partials/health_summary.html -->
    <ul class="text-sm text-aegis-muted space-y-1">
      {% for name, status in checks.items() %}
      <li>
        <span class="text-white">{{ name }}</span>: {{ status }}
      </li>
      {% endfor %}
    </ul>
    ```

2. The fragment route:

    ```python
    # app/components/web_frontend/routes/partials/system.py
    from app.components.web_frontend.main import templates
    from fastapi import APIRouter, Request
    from fastapi.responses import HTMLResponse

    router = APIRouter()


    @router.get("/health-summary", response_class=HTMLResponse, include_in_schema=False)
    async def health_summary(request: Request) -> HTMLResponse:
        from app.services.system.health import get_health_status

        health = await get_health_status()
        return templates.TemplateResponse(
            request=request,
            name="partials/health_summary.html",
            context={"checks": {c.name: c.status for c in health.components.values()}},
        )
    ```

3. Mount it in `main.py`'s `create_web_frontend_app()`:

    ```python
    from app.components.web_frontend.routes.partials.system import (
        router as system_partials_router,
    )

    router.include_router(system_partials_router, prefix="/partials/system")
    ```

4. Use it from any page:

    ```html
    <button hx-get="/partials/system/health-summary"
            hx-target="#health-box"
            class="text-sm text-aegis-teal hover:text-white transition-colors">
      Check health
    </button>
    <div id="health-box"></div>
    ```

Clicking the button issues a GET, and htmx swaps the returned fragment into
`#health-box`. If the fragment carries an inline `<script>`, it runs; that is
the re-execution rule below doing its job.

## Two load-bearing rules

Both of these exist because of real failure modes. Keep them.

### Inline scripts re-execute after swaps

Browsers do not run `<script>` tags injected via `innerHTML`, and `innerHTML`
is exactly how htmx inserts a swapped fragment. Without intervention, an
inline init script inside a partial silently never runs.

`static/js/app.js` fixes this with an `htmx:afterSwap` hook that replaces each
script node in the swapped content with a freshly created one, which the
browser does execute. This is what makes the "partial carries its own little
init script" pattern work. If you remove the hook, partials with inline
scripts break with no error anywhere.

### htmx history is disabled

The base layout sets:

```html
<meta name="htmx-config" content='{"historyCacheSize": 0, "refreshOnHistoryMiss": true}'>
```

htmx's default back-button behavior snapshots the live DOM into localStorage
and re-injects it on history navigation. This DOM is full of Alpine-expanded
templates (`x-if`/`x-for` clones, `x-teleport` copies) and script tags.
Restoring a snapshot re-runs scripts ("identifier already declared") and makes
Alpine re-expand already-expanded templates, duplicating page content once per
back/forward press.

`historyCacheSize: 0` makes every restore a cache miss, and
`refreshOnHistoryMiss` turns a miss into a clean full-page load. Back and
forward still work; they just re-render instead of restoring a snapshot.

## The snackbar

`templates/components/snackbar.html` is included by the base layout, so every
page has a toast surface. It is driven by `sessionStorage`, which means it
survives a reload:

```js
window.appFlashSnackbar('Project saved');
window.location.reload();
```

The snackbar reads the message on mount, clears the key, shows for four
seconds, and can be dismissed early. Use it for any "do something, reload,
confirm it happened" flow.

## The macro kit

`templates/components/macros.html` ships reusable macros. Import what you
need:

```html
{% from "components/macros.html" import primary_button, or_divider %}
```

| Macro | What it is |
|---|---|
| `modal_scrim` | Full-bleed dismiss layer behind a modal. |
| `popover_panel` | The one tooltip panel every hover hint uses. |
| `hover_hint` | Dotted-underline term with a hover definition. |
| `info_tooltip` | Small `?` icon with a click-triggered popover. |
| `primary_button` | The teal action button. |
| `submit_button` | Primary button with a loading spinner; needs `loading` in Alpine scope. |
| `select_field` | Themed combobox replacing the native `<select>`. |
| `password_input` | Password field with a show/hide toggle. |
| `or_divider` | "or" hairline between alternative actions. |

Macros that take a body use `{% call %}`:

```html
{% call info_tooltip() %}<p>Explanation here.</p>{% endcall %}
```

## Template context

Three globals are available in every template, so routes never need to pass
them: `project_name`, `project_description`, and `static()` (covered in
[Asset pipeline](asset-pipeline.md)). Projects with the auth service also get
`auth_enabled` and `registration_enabled`.
