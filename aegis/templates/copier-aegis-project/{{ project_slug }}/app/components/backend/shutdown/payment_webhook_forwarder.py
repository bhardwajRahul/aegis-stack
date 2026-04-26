"""
Stripe webhook auto-forwarder shutdown hook.

Terminates the ``stripe listen`` subprocess launched by the paired
startup hook under ``app/components/backend/startup/``. Graceful first
(``terminate`` / SIGTERM), escalating to ``kill`` / SIGKILL if the
subprocess doesn't exit within a short grace period — mirrors the
convention used by ``app/components/backend/shutdown/cleanup.py``.

No-op when the startup hook didn't launch a subprocess (gate failed,
or the user ran Overseer without payment in test mode).
"""

from app.components.backend.startup import payment_webhook_forwarder as _forwarder
from app.core.log import logger

# How long to wait for the subprocess to exit after ``terminate`` before
# escalating to ``kill``. Stripe CLI shuts down cleanly on SIGTERM in
# well under a second; 3s is a generous ceiling.
_TERMINATE_GRACE_SECONDS = 3.0


async def shutdown_payment_webhook_forwarder() -> None:
    """Terminate the stripe-cli subprocess if one is running."""
    proc = _forwarder.forwarder_process
    if proc is None:
        return

    # Idempotent — if the subprocess already exited (crashed, lost
    # connection, user killed stripe-cli manually), ``poll`` returns the
    # exit code and we skip the shutdown dance.
    if proc.poll() is not None:
        _forwarder.forwarder_process = None
        return

    proc.terminate()
    try:
        proc.wait(timeout=_TERMINATE_GRACE_SECONDS)
    except Exception:
        # ``subprocess.TimeoutExpired`` in practice; catch broadly so a
        # platform quirk can't block shutdown.
        logger.warning(
            "Stripe webhook forwarder did not exit within %.0fs; killing.",
            _TERMINATE_GRACE_SECONDS,
        )
        proc.kill()

    _forwarder.forwarder_process = None
    logger.info("Stripe webhook forwarder stopped")


shutdown_hook = shutdown_payment_webhook_forwarder
