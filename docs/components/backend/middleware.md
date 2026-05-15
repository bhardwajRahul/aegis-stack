# Middleware

Middleware in Aegis is **auto-discovered**. Drop a Python file into
`app/components/backend/middleware/` that exports a
`register_middleware` function, and it runs on the next start. No
central registry, no import order to manage.

## The Contract

```python
# app/components/backend/middleware/your_middleware.py
from fastapi import FastAPI

def register_middleware(app: FastAPI) -> None:
    app.add_middleware(YourMiddleware, ...)
```

That's the whole API. A few rules worth knowing:

- **`register_middleware` is synchronous.** It runs at app build time,
  before the event loop starts. Use `def`, not `async def`. If you
  need async setup, do it in a [startup hook](lifecycle.md) and read
  the result from settings or a module-level cache inside
  `register_middleware`.
- **Files beginning with `_` are skipped.** Use this for shared
  helpers in the directory.
- **Registration order is not guaranteed.** If two middleware modules
  must compose in a specific order, define both classes in the same
  file and register them in one `register_middleware` call so the
  order is explicit.
- **A module that doesn't export `register_middleware` is silently
  ignored.** Intentional. If your new middleware never fires, check
  the function name and that the filename isn't prefixed with `_`.
- **Import errors are logged, not raised.** One broken middleware
  won't take down the boot. Watch the logs.

## What Ships In The Templates

The following middleware come with every generated project. Some are
gated on the services you selected at `aegis init` time.

### Performance

Registered always. Times every HTTP request and surfaces live
per-endpoint stats through the Server modal's Performance tab and
`/api/v1/metrics/*`. In-process and ephemeral, with no external
dependencies.

See [Performance Middleware](middleware/performance.md) for what you
see, how to read it, and when to reach for observability instead.

### CORS

Registered always. Out of the box, allows the local Flet dev
frontend and the FastAPI docs UI to call the backend with
credentials. To open up for a deployed frontend, widen the allowed
origins list in the CORS module, or replace the hard-coded values
with a setting.

### OAuth Session

Registered when the auth service is included with at least one OAuth
provider enabled. Holds the OAuth state and PKCE verifier between
the redirect to the provider and the callback. Without it, the OAuth
round-trip can't be verified.

Two settings to know:

- `OAUTH_SESSION_SECRET`: signing secret for the session cookie.
- `SESSION_COOKIE_SECURE`: explicit override of the cookie's secure
  flag. Defaults to secure in every environment except
  `APP_ENV=dev`. Set to `false` for prod-over-plain-HTTP setups
  where browsers would otherwise drop the cookie.

### Logfire Tracing

Registered when the observability component is included. Wires up
Logfire instrumentation for FastAPI, HTTPX, and (if present)
SQLAlchemy and Redis. When `LOGFIRE_TOKEN` is unset, traces still
run locally and nothing is shipped to Logfire cloud.

Polling endpoints used by the dashboard are excluded from tracing
on purpose; otherwise they'd drown out every other span.

## Authoring A Custom Middleware

Drop one file, export one function. Example: inject and echo a
request ID.

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
    app.add_middleware(RequestIDMiddleware)
```

Restart the backend, and the Lifecycle tab on the Server card shows
your new middleware in the stack.

!!! example "Musings: Backend Middleware Auto-Discovery (November 22nd, 2025)"
    I'm not sure how I ultimately feel about the auto-discovery middleware pattern. I don't have enough experience with FastAPI plugins yet, but it's something I'm thinking about as the architecture evolves.

    The current approach works well for explicit component registration, but auto-discovery could reduce boilerplate at the cost of making the registration flow less obvious. Trade-offs worth considering as Aegis Stack matures.

## See Also

- [Lifecycle](lifecycle.md) for setup work that needs the event loop.
- [Authentication Integration](auth.md) for the rate-limiter
  dependency pattern, which lives alongside middleware but is
  consumed as a FastAPI dependency rather than registered as one.
