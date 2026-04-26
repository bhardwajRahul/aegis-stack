"""Browser-facing HTML pages for payment checkout redirects.

These are the default landing targets for Stripe's success_url and cancel_url.
Users can override the URLs per-checkout (via CheckoutRequest fields) or
app-wide (via PAYMENT_SUCCESS_URL / PAYMENT_CANCEL_URL settings).

Inline HTML with the Aegis design palette (Tailwind + DaisyUI via CDN).
When the project gains a first-class server-rendered frontend component,
these handlers become thin template renders; the URLs stay stable.
"""

import html as _html
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/payment", tags=["payment-pages"])

# Stripe session IDs are opaque tokens of the shape ``cs_test_xxx`` /
# ``cs_live_xxx``. Validating against this narrow allowlist (plus escaping
# the remainder) defends against XSS even if Stripe ever broadens the
# alphabet: a hostile query param like ``</p><script>`` fails the regex
# and renders nothing.
_SESSION_ID_RE = re.compile(r"^cs_(test|live)_[A-Za-z0-9]+$")


def _page(
    status: str,
    heading: str,
    body: str,
    session_line: str = "",
) -> str:
    """Render the shared page shell with a status-specific dot and content."""
    dot_class = "dot-success" if status == "success" else "dot-cancel"
    label = "Payment"
    daisyui_url = "https://cdn.jsdelivr.net/npm/daisyui@4.12.23/dist/full.min.css"
    back_btn_classes = (
        "btn-aegis inline-flex items-center justify-center "
        "w-full rounded-lg px-4 py-3 text-sm"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{heading}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="{daisyui_url}" rel="stylesheet">
<style>
  :root {{
    --bg: #090B0D;
    --card: #111418;
    --border: #1F242B;
    --text: #EEF1F4;
    --muted: #8B94A0;
    --brand: #17CCBF;
  }}
  html, body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }}
  .aegis-card {{
    background: var(--card);
    border: 1px solid var(--border);
  }}
  .aegis-muted {{ color: var(--muted); }}
  .dot {{
    width: 10px;
    height: 10px;
    border-radius: 9999px;
    display: inline-block;
  }}
  .dot-success {{
    background: var(--brand);
    box-shadow: 0 0 0 4px rgba(23, 204, 191, 0.15);
  }}
  .dot-cancel {{
    background: var(--muted);
    box-shadow: 0 0 0 4px rgba(139, 148, 160, 0.12);
  }}
  .btn-aegis {{
    background: var(--brand);
    color: var(--bg);
    font-weight: 600;
    transition: filter 150ms ease-out;
  }}
  .btn-aegis:hover {{ filter: brightness(1.1); }}
  .btn-ghost {{
    border: 1px solid var(--border);
    color: var(--text);
  }}
  .btn-ghost:hover {{ background: rgba(255,255,255,0.03); }}
</style>
</head>
<body class="min-h-screen flex items-center justify-center px-6">
  <div class="aegis-card rounded-2xl p-10 max-w-md w-full">
    <div class="flex items-center gap-3 mb-6">
      <span class="dot {dot_class}"></span>
      <span class="text-xs tracking-widest uppercase aegis-muted">{label}</span>
    </div>
    <h1 class="text-2xl font-semibold mb-2">{heading}</h1>
    <p class="text-sm aegis-muted mb-8">{body}</p>
    <a href="/dashboard/" class="{back_btn_classes}">Back to dashboard</a>
    {session_line}
  </div>
</body>
</html>"""


@router.get("/success", response_class=HTMLResponse)
def payment_success(session_id: str | None = None) -> HTMLResponse:
    """Default landing page after a successful Stripe checkout."""
    session_line = ""
    if session_id and _SESSION_ID_RE.match(session_id):
        safe_session_id = _html.escape(session_id)
        session_line = (
            f'<p class="text-xs aegis-muted mt-6 font-mono break-all">'
            f"session_id: {safe_session_id}</p>"
        )
    html = _page(
        status="success",
        heading="Payment received",
        body="Thanks. You'll get a receipt by email shortly.",
        session_line=session_line,
    )
    return HTMLResponse(content=html)


@router.get("/cancel", response_class=HTMLResponse)
def payment_cancel() -> HTMLResponse:
    """Default landing page after an abandoned Stripe checkout."""
    html = _page(
        status="cancel",
        heading="Payment cancelled",
        body="You weren't charged. Feel free to try again when you're ready.",
    )
    return HTMLResponse(content=html)
