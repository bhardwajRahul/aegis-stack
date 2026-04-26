# Provider Setup Guide

This guide walks you through setting up Stripe and running your first checkout end-to-end.

## 1. Add the Service

If you didn't include the payment service at project creation, add it now:

```bash
aegis add-service payment
```

This drops in the payment models, REST endpoints, CLI commands, and dashboard card, and installs the `stripe` Python SDK.

## 2. Get Your Stripe Secret Key

1. Sign up at [dashboard.stripe.com](https://dashboard.stripe.com) (free, no credit card required).
2. **Confirm you're in test mode.** New accounts default to test mode, and the dashboard shows a **Test mode** toggle near the top. Leave it on until you're ready to accept real payments. Test keys are prefixed `sk_test_` / `pk_test_`; live keys use `sk_live_` / `pk_live_`.
3. On the dashboard home you'll see two API keys:
    - **Publishable key** (`pk_test_...`): **ignore this.** It's only used for client-side Stripe.js/Elements integrations. This service uses Stripe's hosted Checkout redirect and doesn't need the publishable key anywhere.
    - **Secret key** (`sk_test_...`): **copy this one.**
4. Add it to `.env`:

    ```bash
    STRIPE_SECRET_KEY=sk_test_...
    ```

!!! note "Test vs. live keys"
    Your **test** secret key stays visible in the dashboard. You can re-copy it from [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) any time. **Live** secret keys are different: Stripe reveals a live key once and then masks it, so you must save it securely when it's first shown. If you lose a live key, roll a new one from the same page.

## 3. Get Your Webhook Signing Secret

Unlike the secret key, the webhook signing secret is tied to a specific webhook endpoint, so you get it _after_ you start forwarding events, not at signup.

### Local development

**If you're running the Overseer webserver** (`make serve` or `docker compose up`), webhook forwarding is automatic when `stripe-cli` is installed on your PATH, you're authenticated (`stripe login`), and `STRIPE_SECRET_KEY` is a test key. On startup the app launches `stripe listen` as a supervised subprocess, captures the ephemeral signing secret from its stdout, and injects it into the payment provider at runtime — no `.env` edit needed. You'll see:

```
Stripe webhook forwarder started: stripe listen → /api/v1/payment/webhook
Stripe webhook signing secret captured from stripe-cli
```

in the server logs. Shutting down the webserver terminates the subprocess cleanly.

The auto-forwarder is skipped when any of the following is true, so your setup wins:

- `STRIPE_WEBHOOK_SECRET` is already set in `.env` (explicit override — you're using a tunnel like ngrok or the Stripe dashboard endpoint).
- `STRIPE_SECRET_KEY` is a live key (`sk_live_...`) — production uses the Stripe dashboard webhook, never a local subprocess.
- `stripe-cli` isn't on PATH, or the user hasn't run `stripe login`.

**Foreground alternative**: if you'd rather run the forwarder in a dedicated terminal (easier to watch event logs), the CLI helper is still available:

```bash
my-app payment webhook
```

It shells to `stripe listen --forward-to localhost:8000/api/v1/payment/webhook` and prints:

```
> Ready! Your webhook signing secret is whsec_...
```

Copy that `whsec_...` value into `.env` as `STRIPE_WEBHOOK_SECRET` and restart the webserver — doing so disables the auto-forwarder so you don't end up with two listeners.

See [CLI Commands → webhook](cli.md#webhook) for details including platform-specific `stripe-cli` install instructions.

### Production

1. Go to [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks) and click **Add endpoint**.
2. Endpoint URL: `https://yourdomain.com/api/v1/payment/webhook`.
3. Select the events you want to receive (at minimum: `checkout.session.completed`, `payment_intent.succeeded`, `payment_intent.payment_failed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.*`, `charge.refunded`).
4. Click **Reveal** on the signing secret and copy the `whsec_...` value.

### Either environment

Add it to `.env` and restart the webserver:

```bash
STRIPE_WEBHOOK_SECRET=whsec_...
```

## 4. Verify Connectivity

```bash
my-app payment status
```

You should see **Status: Connected** and **Mode: TEST**. If not, see [Troubleshooting](#troubleshooting) below.

## 5. Create a Product and Price

In the Stripe dashboard under **Products → Add product**, create one with a **Price**. Note two things:

- The **Price ID** (`price_xxx`): you'll pass this to `/checkout`.
- The **pricing model**: choose **One off** for single-charge products or **Recurring** for subscriptions. This must match the `mode` you send to the checkout endpoint (`payment` vs. `subscription`); otherwise the API returns a 400 with Stripe's explanation.

## 6. Create Your First Checkout Session

```bash
curl -X POST http://localhost:8000/api/v1/payment/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_xxx",
    "mode": "payment"
  }'
```

The response contains a `checkout_url`. Open it in your browser to reach Stripe's hosted checkout page.

### About `success_url` and `cancel_url`

When you omit these fields (as in the example above), the service falls back to built-in default routes at `/payment/success` and `/payment/cancel`. These ship with the service and are styled to match the Aegis palette, so a fresh project works end-to-end with no extra wiring.

Override globally via `.env`:

```bash
PAYMENT_SUCCESS_URL=https://yourdomain.com/thanks?session_id={CHECKOUT_SESSION_ID}
PAYMENT_CANCEL_URL=https://yourdomain.com/checkout
```

Or per-request by passing `success_url` / `cancel_url` in the checkout body. Request body wins over settings wins over built-in defaults.

See [Test Cards](#test-cards) below for numbers that simulate different outcomes. See [Examples → One-time Payment](examples.md#one-time-payment) for a full end-to-end flow including handling the success redirect.

## Test Cards

On Stripe's hosted checkout in test mode, the card number you enter determines the outcome. The page doesn't auto-decline; you control the result by picking the right number.

For every test card: use any future expiry (e.g. `12/34`), any 3-digit CVC (Amex uses 4 digits), and any ZIP/postal code.

!!! warning "Test mode only"
    Never enter real card details, even for a test charge. Stripe's terms of service prohibit testing in live mode with real payment methods. Stick to the numbers below while `STRIPE_SECRET_KEY` is a `sk_test_...` key.

### Successful payments

| Card Number | Brand | Behavior |
|-------------|-------|----------|
| `4242 4242 4242 4242` | Visa | Always succeeds |
| `5555 5555 5555 4444` | Mastercard | Always succeeds |
| `3782 822463 10005` | American Express | Always succeeds |
| `6011 1111 1111 1117` | Discover | Always succeeds |

### Declined payments

| Card Number | Decline code |
|-------------|--------------|
| `4000 0000 0000 0002` | `generic_decline` |
| `4000 0000 0000 9995` | `insufficient_funds` |
| `4000 0000 0000 9987` | `lost_card` |
| `4000 0000 0000 9979` | `stolen_card` |

The server returns a `card_declined` error with the matching `decline_code`. Stripe Checkout displays a user-facing message ("Your card was declined." etc.) and keeps the user on the payment page.

### 3D Secure / authentication

| Card Number | Behavior |
|-------------|----------|
| `4000 0000 0000 3220` | 3DS authentication is required and must complete for the payment to succeed |
| `4000 0025 0000 3155` | Requires 3DS for off-session payments until the card is saved for future use |
| `4000 0084 0000 1629` | 3DS authenticates successfully, but the charge is then declined (`card_declined`) |
| `4000 0000 0000 3055` | 3DS is supported and may be prompted, but is not required |
| `4242 4242 4242 4242` | Supports 3DS but isn't enrolled, so no extra step is shown |

### Fraud / risk simulation

| Card Number | Behavior |
|-------------|----------|
| `4100 0000 0000 0019` | **Always blocked** by Stripe's built-in rules (payment fails) |
| `4000 0000 0000 4954` | Risk score `highest`; payment **succeeds** unless you've enabled Radar rules to auto-block |
| `4000 0000 0000 9235` | Risk score `elevated`; payment **succeeds** unless Radar rules say otherwise |

Only the first card auto-declines. The other two just raise the risk score on the resulting charge, which is how Stripe lets you test flagging-for-review logic in your own code or in [Radar rules](https://dashboard.stripe.com/test/radar). If you want one of them to block, add a rule like "Block if `:risk_level: = 'highest'`" in Radar first.

### Invalid card

| Input | Result |
|-------|--------|
| Any random number that passes the Luhn check | `Your card number is invalid.` (inline on the form) |

### Full reference

Stripe publishes additional cards for specific countries, brands, refund scenarios, and error codes not listed above. See the complete list at [docs.stripe.com/testing](https://docs.stripe.com/testing).

## Going Live

When you're ready to accept real payments:

1. In the Stripe dashboard, switch the **Test mode** toggle off, complete account activation (business info, bank account), and then grab your **live** secret key (`sk_live_...`).
2. Create a **production webhook endpoint** pointing at your deployed URL and copy its new `whsec_...`.
3. Update production `.env` with the live values. Never commit live keys.

## Troubleshooting

**`Status: Disconnected` even though the key is set**: the CLI and webserver both read `STRIPE_SECRET_KEY` via pydantic `Settings()`, which loads from `.env`. If you set the key directly in your shell (not `.env`), it won't be seen by a process that only loads the dotenv file. Prefer `.env`.

**`Extra inputs are not permitted` on webserver startup**: the webserver's `Settings` model is missing a declared field for one of the `STRIPE_*` env vars. Check `app/core/config.py` for `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` declarations under the payment block.

**`You specified 'payment' mode but passed a recurring price`**: your Price was configured as recurring in Stripe but you sent `"mode": "payment"` in the checkout request. Either change `mode` to `"subscription"` or create a separate one-off Price for single charges.

**Webhook signature verification fails**: the `STRIPE_WEBHOOK_SECRET` in `.env` must match the signing secret for the specific endpoint delivering events. Local `stripe listen` and production dashboard webhooks have **different** secrets; don't mix them. If the Overseer auto-forwarder is running, the runtime-captured secret wins over `.env` — unset `STRIPE_WEBHOOK_SECRET` to let the auto-forwarder manage it, or set it explicitly to disable auto-forwarding.

**Auto-forwarder skipped, events never arrive**: check the server logs for one of these lines:

- `Stripe CLI not installed; skipping auto-webhook-forwarder` — install stripe-cli (`brew install stripe/stripe-cli/stripe` on macOS) or run `my-app payment webhook` manually.
- `Stripe CLI is installed but not authenticated` — run `stripe login` once, then restart the webserver.
- `STRIPE_SECRET_KEY is not a test key` — the auto-forwarder only runs in test mode; live deployments must configure a production webhook endpoint in the Stripe dashboard.

**Docker compose**: the webserver image installs `stripe-cli` when the payment service is included (see the `Install stripe-cli` block in `Dockerfile`). The auto-forwarder authenticates via `--api-key $STRIPE_SECRET_KEY` at runtime, so no interactive `stripe login` is needed inside the container. If you see `Stripe CLI not installed` from a compose run, your image was built before this feature landed — rebuild it with `docker compose build --no-cache webserver`.
