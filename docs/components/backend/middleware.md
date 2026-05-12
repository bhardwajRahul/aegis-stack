# Middleware

Middleware in Aegis is **auto-discovered**. Any module dropped into
`app/components/backend/middleware/` that exposes a `register_middleware`
function is picked up at app build time. There is no central registry to
edit and no import order to manage by hand.

## The Auto-Discovery Contract

`app/components/backend/hooks.py` walks `middleware/` at startup, imports
every `*.py` file whose name does not begin with `_`, and calls
`register_middleware(app)` on any module that defines it.

```python
# app/components/backend/middleware/your_middleware.py
from fastapi import FastAPI

def register_middleware(app: FastAPI) -> None:
    """Auto-discovered middleware registration."""
    app.add_middleware(YourMiddleware, ...)
```

A few rules worth knowing up front:

- **The function is synchronous.** Discovery happens before the lifespan
  starts, so `register_middleware` runs at import time, not in the event
  loop. Use `def`, not `async def`.
- **Files beginning with `_` are skipped.** Use this for shared helpers
  inside the directory.
- **Order is filesystem order.** `Path.glob("*.py")` does not promise a
  stable ordering across platforms. If two middleware modules must run in
  a specific order, put them in the same file.
- **Modules that fail to import are logged, not raised.** Discovery
  catches exceptions per file so one broken middleware does not take down
  the boot. Watch the logs.

A module in `middleware/` that does **not** export `register_middleware`
is ignored by the discovery loop. Keep modules in this directory that
actually register middleware; security primitives consumed as FastAPI
dependencies live under
[`app/components/backend/security/`](auth.md#2-rate-limiting-on-auth-endpoints)
and are exposed through `app/components/backend/api/deps.py`.

## Middleware That Ships In The Templates

The following modules live under
`app/components/backend/middleware/` in a generated project. Some are
gated on the services you selected at `aegis init` time.

### `cors.py`

Registered always. Allows `http://localhost:3000` and
`http://localhost:8080` with credentials and arbitrary methods and
headers. The defaults exist for the Flet dev frontend and the FastAPI
docs UI on `:8080`. To widen for a deployed frontend, edit the
`allow_origins` list in this file, or replace it with values pulled from
settings.

```python
# app/components/backend/middleware/cors.py
def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### `session.py` (auth + OAuth only)

Registered when the auth service is included with OAuth providers
enabled. Wraps Starlette's `SessionMiddleware` so Authlib can stash the
OAuth `state` and PKCE verifier between `/start` and `/callback`. Without
it, the OAuth round-trip can't be verified.

Two settings matter:

- `OAUTH_SESSION_SECRET`: the signing secret for the session cookie.
- `SESSION_COOKIE_SECURE`: explicit override of the `https_only` flag.
  When unset, the cookie is marked secure in every environment except
  `APP_ENV=dev`. The escape hatch (`SESSION_COOKIE_SECURE=false`) exists
  for prod-over-plain-HTTP deployments where the browser would otherwise
  silently drop the cookie.

### `logfire_tracing.py` (observability only)

Registered when the observability component is included. Configures
Logfire with the project name and `APP_ENV`, then calls
`logfire.instrument_fastapi(app, excluded_urls="/health/.*|/dashboard/.*")`
and `logfire.instrument_httpx()`. When the database or Redis components
are present it also instruments SQLAlchemy and Redis. When
`LOGFIRE_TOKEN` is unset, instrumentation still runs locally but nothing
is shipped to Logfire cloud.

`/health/*` and `/dashboard/*` are excluded from the FastAPI
instrumentation on purpose: Overseer polls these every few seconds and
they would otherwise dominate every trace view.

## Authoring A Custom Middleware

The contract is one file, one function. To add request ID injection:

```python
# app/components/backend/middleware/request_id.py
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_middleware(app: FastAPI) -> None:
    """Auto-discovered middleware registration."""
    app.add_middleware(RequestIDMiddleware)
```

Drop the file, restart the backend, and Overseer's Lifecycle tab will
show the new middleware in the stack.

!!! example "Musings: Backend Middleware Auto-Discovery (November 22nd, 2025)"
    I'm not sure how I ultimately feel about the auto-discovery middleware pattern. I don't have enough experience with FastAPI plugins yet, but it's something I'm thinking about as the architecture evolves.

    The current approach works well for explicit component registration, but auto-discovery could reduce boilerplate at the cost of making the registration flow less obvious. Trade-offs worth considering as Aegis Stack matures.

## Pitfalls

- **Registration order is not deterministic across platforms.** If two
  middleware modules must compose in a specific order, define both
  classes in the same file and register them in one
  `register_middleware` call so the order is explicit.
- **`register_middleware` is sync.** If you need to do async setup
  (open a connection, fetch a remote config), do it in a
  [startup hook](lifecycle.md) and read the result from settings or a
  module-level cache inside `register_middleware`.
- **A middleware module without `register_middleware` is silently
  ignored.** That is intentional, but if your new middleware never
  fires, check the function name and that the file isn't prefixed with
  `_`.

## Reference

- `app/components/backend/hooks.py`: discovery implementation
  (`BackendHooks.discover_and_register_middleware`).
- `app/components/backend/middleware/`: the built-in modules above.
- [Lifecycle](lifecycle.md): for setup work that needs the event loop.
- [Authentication Integration](auth.md): the rate-limiter dependency
  pattern.
