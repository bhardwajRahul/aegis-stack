"""
Tests for the Overseer Stripe webhook auto-forwarder.

The hook launches ``stripe listen`` as a subprocess when the gate
passes and populates a runtime webhook secret for the payment provider.
These tests exercise each gate branch plus the secret-parse and
shutdown paths with the subprocess fully mocked — no real stripe-cli
invocation.
"""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.components.backend.shutdown import (
    payment_webhook_forwarder as shutdown_mod,
)
from app.components.backend.startup import payment_webhook_forwarder as startup_mod
from app.services.payment.providers import stripe as stripe_provider_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_module_state() -> Generator[None, None, None]:
    """Clear the runtime secret and subprocess handle between tests."""
    stripe_provider_mod._RUNTIME_WEBHOOK_SECRET = None
    startup_mod.forwarder_process = None
    yield
    stripe_provider_mod._RUNTIME_WEBHOOK_SECRET = None
    startup_mod.forwarder_process = None


def _fake_settings(
    secret_key: str = "sk_test_abc",
    webhook_secret: str = "",
    port: int = 8000,
) -> SimpleNamespace:
    return SimpleNamespace(
        STRIPE_SECRET_KEY=secret_key,
        STRIPE_WEBHOOK_SECRET=webhook_secret,
        PORT=port,
    )


# ---------------------------------------------------------------------------
# Gate branches
# ---------------------------------------------------------------------------


class TestForwarderGate:
    """``_should_auto_forward`` returns False with a reason on any skip."""

    def test_skips_when_not_test_mode(self) -> None:
        with patch.object(
            startup_mod, "settings", _fake_settings(secret_key="sk_live_abc")
        ):
            ok, reason = startup_mod._should_auto_forward()
        assert ok is False
        assert "not a test key" in reason

    def test_skips_when_webhook_secret_set(self) -> None:
        with patch.object(
            startup_mod,
            "settings",
            _fake_settings(webhook_secret="whsec_user_set"),
        ):
            ok, reason = startup_mod._should_auto_forward()
        assert ok is False
        assert "set explicitly" in reason

    def test_skips_when_cli_missing(self) -> None:
        with (
            patch.object(startup_mod, "settings", _fake_settings()),
            patch.object(startup_mod.shutil, "which", return_value=None),
        ):
            ok, reason = startup_mod._should_auto_forward()
        assert ok is False
        assert "Stripe CLI not installed" in reason

    def test_allows_when_all_gates_pass(self) -> None:
        with (
            patch.object(startup_mod, "settings", _fake_settings()),
            patch.object(
                startup_mod.shutil, "which", return_value="/usr/local/bin/stripe"
            ),
        ):
            ok, reason = startup_mod._should_auto_forward()
        assert ok is True
        assert reason == ""


# ---------------------------------------------------------------------------
# Full startup with a mocked subprocess
# ---------------------------------------------------------------------------


class TestForwarderStartup:
    """End-to-end path: gate passes → Popen → secret line parsed → stored."""

    @pytest.mark.asyncio
    async def test_startup_skips_when_gate_fails(self) -> None:
        """Skip path must never touch subprocess or the runtime secret."""
        with (
            patch.object(
                startup_mod, "settings", _fake_settings(secret_key="sk_live_abc")
            ),
            patch.object(startup_mod.subprocess, "Popen") as popen,
        ):
            await startup_mod.startup_payment_webhook_forwarder()

        popen.assert_not_called()
        assert startup_mod.forwarder_process is None
        assert stripe_provider_mod._RUNTIME_WEBHOOK_SECRET is None

    @pytest.mark.asyncio
    async def test_startup_captures_secret_from_stdout(self) -> None:
        """Stripe-cli banner line yields a ``whsec_...`` → runtime secret."""
        banner = "Ready! Your webhook signing secret is whsec_abc123XYZ (^C to quit)\n"
        fake_stdout = MagicMock()
        # ``readline`` returns one line then signals EOF with ``""`` so the
        # background drain exits cleanly.
        fake_stdout.readline.side_effect = [banner, ""]
        fake_proc = MagicMock(stdout=fake_stdout)

        with (
            patch.object(startup_mod, "settings", _fake_settings()),
            patch.object(
                startup_mod.shutil, "which", return_value="/usr/local/bin/stripe"
            ),
            patch.object(startup_mod.subprocess, "Popen", return_value=fake_proc),
        ):
            await startup_mod.startup_payment_webhook_forwarder()

        assert startup_mod.forwarder_process is fake_proc
        assert stripe_provider_mod._RUNTIME_WEBHOOK_SECRET == "whsec_abc123XYZ"

    @pytest.mark.asyncio
    async def test_startup_passes_api_key_to_stripe_listen(self) -> None:
        """``stripe listen`` is invoked with ``--api-key``.

        No ``stripe login`` is required.
        """
        banner = "Ready! Your webhook signing secret is whsec_xyz\n"
        fake_stdout = MagicMock()
        fake_stdout.readline.side_effect = [banner, ""]
        fake_proc = MagicMock(stdout=fake_stdout)

        with (
            patch.object(
                startup_mod,
                "settings",
                _fake_settings(secret_key="sk_test_abc123"),
            ),
            patch.object(
                startup_mod.shutil, "which", return_value="/usr/local/bin/stripe"
            ),
            patch.object(
                startup_mod.subprocess, "Popen", return_value=fake_proc
            ) as popen,
        ):
            await startup_mod.startup_payment_webhook_forwarder()

        args = popen.call_args[0][0]
        assert args[:4] == ["stripe", "listen", "--api-key", "sk_test_abc123"]
        assert "--forward-to" in args


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


class TestForwarderShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_terminates_running_subprocess(self) -> None:
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None  # still running
        startup_mod.forwarder_process = fake_proc

        await shutdown_mod.shutdown_payment_webhook_forwarder()

        fake_proc.terminate.assert_called_once()
        fake_proc.wait.assert_called_once()
        assert startup_mod.forwarder_process is None

    @pytest.mark.asyncio
    async def test_shutdown_noop_when_no_subprocess(self) -> None:
        startup_mod.forwarder_process = None
        # Should not raise.
        await shutdown_mod.shutdown_payment_webhook_forwarder()

    @pytest.mark.asyncio
    async def test_shutdown_kills_if_terminate_times_out(self) -> None:
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        fake_proc.wait.side_effect = Exception("timeout")
        startup_mod.forwarder_process = fake_proc

        await shutdown_mod.shutdown_payment_webhook_forwarder()

        fake_proc.terminate.assert_called_once()
        fake_proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# StripeProvider picks up the runtime override
# ---------------------------------------------------------------------------


class TestStripeProviderVerifyWebhook:
    """``verify_webhook`` must return a WebhookEvent with a plain-dict
    ``data`` field, not a ``stripe.StripeObject`` — the previous bug.

    Regression: ``stripe.StripeObject`` is dict-like but not a ``dict``
    instance. Pydantic v2 ``dict[str, Any]`` refuses to coerce it, and
    the workaround ``dict(obj)`` raises ``KeyError: 0`` on some event
    types (e.g. ``product.created``). Fix re-parses the verified raw
    JSON payload, giving us plain nested dicts.
    """

    def test_verify_webhook_returns_plain_dict_data(self) -> None:
        """Real-shape Stripe payload → WebhookEvent.data is a dict."""
        import json
        from unittest.mock import MagicMock, patch

        from app.services.payment.providers.stripe import StripeProvider

        payload_dict = {
            "id": "evt_test",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_intent": "pi_test_123",
                    "amount_total": 2500,
                    "currency": "usd",
                    "mode": "payment",
                    "customer": None,
                }
            },
        }
        payload = json.dumps(payload_dict).encode()
        fake_event = MagicMock(type="checkout.session.completed")

        provider = StripeProvider()
        provider._webhook_secret = "whsec_test"

        with patch(
            "app.services.payment.providers.stripe.stripe.Webhook.construct_event",
            return_value=fake_event,
        ):
            import asyncio

            result = asyncio.run(provider.verify_webhook(payload, "sig"))

        assert result.event_type == "checkout.session.completed"
        assert isinstance(result.data, dict)
        assert result.data["id"] == "cs_test_123"
        assert result.data["amount_total"] == 2500


class TestStripeProviderRuntimeOverride:
    def test_provider_prefers_runtime_secret(self) -> None:
        """Runtime secret beats ``settings.STRIPE_WEBHOOK_SECRET``."""
        from app.services.payment.providers.stripe import (
            StripeProvider,
            set_runtime_webhook_secret,
        )

        set_runtime_webhook_secret("whsec_from_runtime")
        with patch.object(
            stripe_provider_mod,
            "settings",
            _fake_settings(webhook_secret="whsec_from_env"),
        ):
            provider = StripeProvider()

        assert provider._webhook_secret == "whsec_from_runtime"

    def test_provider_falls_back_to_settings(self) -> None:
        """When no runtime secret is set, settings value is used."""
        from app.services.payment.providers.stripe import StripeProvider

        assert stripe_provider_mod._RUNTIME_WEBHOOK_SECRET is None
        with patch.object(
            stripe_provider_mod,
            "settings",
            _fake_settings(webhook_secret="whsec_from_env"),
        ):
            provider = StripeProvider()

        assert provider._webhook_secret == "whsec_from_env"
