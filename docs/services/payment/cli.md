# CLI Commands

Command-line interface reference for the Payment Service.

## Overview

```bash
my-app payment --help
```

Available subcommands:

| Command | Purpose |
|---------|---------|
| `status` | Show provider connectivity and a transaction/revenue summary |
| `transactions` | List recent transactions, optionally filtered by status |
| `disputes` | List chargebacks and early fraud warnings, with deadlines |
| `webhook` | Forward live Stripe webhook events to the local server |
| `seed` | Populate the database with fake data for dashboard testing |

## status

Check provider connectivity, test/live mode, and a summary of transaction activity.

```bash
my-app payment status
```

**Output**

```
Payment Service Status

  Provider                Stripe
  Mode                    TEST
  Status                  Connected
  API Version             2026-03-25.dahlia
  Transactions            12
  Revenue                 $1,240.00
  Active Subscriptions    3
```

If `Status: Disconnected`, the CLI prints a warning explaining the cause (missing key, auth failure, etc.) See the [setup troubleshooting guide](setup.md#troubleshooting).

## transactions

List recent transactions in a table.

```bash
my-app payment transactions              # most recent 20
my-app payment transactions --limit 50   # more
my-app payment transactions -n 5         # shorthand
my-app payment transactions -s succeeded # filter by status
```

**Flags**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--limit` | `-n` | `20` | Number of transactions to show |
| `--status` | `-s` | (none) | Filter by status (`succeeded`, `pending`, `failed`, `refunded`, `partially_refunded`) |

**Output**

```
                  Transactions (12 total)
+------+-----------+-----------+----------+----------+------------------+
| ID   | Type      | Status    | Amount   | Currency | Date             |
+------+-----------+-----------+----------+----------+------------------+
| 42   | charge    | succeeded | $120.00  | USD      | 2026-04-17 14:22 |
| 41   | refund    | refunded  | $50.00   | USD      | 2026-04-17 12:10 |
| ...                                                                    |
+------+-----------+-----------+----------+----------+------------------+
```

Transactions come from the local `payment_transaction` table, populated by webhook events from Stripe.

## disputes

List chargebacks and early fraud warnings recorded by the webhook handler. Each row includes its status (warning_issued → needs_response → under_review → won/lost/charge_refunded), reason code, amount, and the evidence-submission deadline when one applies.

```bash
my-app payment disputes                     # all disputes
my-app payment disputes -s open             # warning_issued, needs_response, under_review
my-app payment disputes -s needs_response   # any specific status
```

**Flags**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--status` | `-s` | (none) | `open` shortcut, or one of: `warning_issued`, `warning_closed`, `needs_response`, `under_review`, `won`, `lost`, `charge_refunded` |

## seed

Populate the payment database with fake data across every UI state — useful for eyeballing the dashboard's Payment card and tabs without running real Stripe charges. Creates transactions (succeeded, pending, failed, refunded, partially refunded, canceled, subscription-type), subscriptions (active, trialing, past due, canceled, cancelling-at-period-end), and disputes (every lifecycle status plus different reason codes).

```bash
my-app payment seed            # add fake rows to existing data
my-app payment seed --reset    # wipe then re-seed (idempotent re-run)
my-app payment seed --clear    # wipe only, no seed
```

**Flags**

| Flag | Description |
|------|-------------|
| `--reset` | Delete all existing payment rows (except the provider) before seeding |
| `--clear` | Delete all existing payment rows and exit without seeding |

After seeding, the dashboard Payment card shows populated Overview metrics, the Transactions tab lists 15 rows across all statuses, Subscriptions shows 5 plans, and Disputes shows 7 rows covering every dispute lifecycle state including one with an evidence deadline inside 5 days.

!!! warning "Dev-only"
    `seed` writes directly to the database and never calls Stripe. Do not run this against a production database, and do not assume any seeded row corresponds to a real Stripe object. Use `--reset` freely during dashboard/QA work; never deploy the seed command behind an authenticated endpoint.

## webhook

Forward live Stripe webhook events from your Stripe account to your local webserver. Essential for testing webhook-driven flows (subscription renewals, refund confirmations, etc.) during development.

```bash
my-app payment webhook          # defaults to port 8000
my-app payment webhook -p 8080  # custom port
```

Under the hood this wraps:

```bash
stripe listen --forward-to localhost:8000/api/v1/payment/webhook
```

**Flags**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--port` | `-p` | `8000` | Local webserver port |

### First-time setup

The command shells out to the [Stripe CLI](https://stripe.com/docs/stripe-cli). If it's not yet installed, `my-app payment webhook` will detect that and print platform-specific install instructions:

=== "macOS"

    ```bash
    brew install stripe/stripe-cli/stripe
    ```

=== "Windows"

    ```powershell
    scoop install stripe
    ```

=== "Linux"

    See the [official install guide](https://stripe.com/docs/stripe-cli#install) for Debian/Ubuntu APT, Red Hat/Fedora YUM, or a pre-built binary.

After install, authenticate the CLI once with your Stripe account:

```bash
stripe login
```

This opens a browser to pair the CLI with your dashboard. Subsequent `my-app payment webhook` runs will just work.

### Getting the webhook signing secret

When `stripe listen` starts, it prints a line like:

```
> Ready! Your webhook signing secret is whsec_...
```

Copy that `whsec_...` value and set it as `STRIPE_WEBHOOK_SECRET` in `.env`, then restart the webserver so the new value is picked up.

!!! note "Local vs. production secrets"
    The signing secret from `stripe listen` is unique to your local `stripe-cli` session. Your production webhook endpoint in the Stripe dashboard has a different `whsec_...`; use the environment-appropriate value in each deployment.

### Triggering test events

While `my-app payment webhook` is running, you can fire synthetic events from another terminal using the Stripe CLI directly:

```bash
stripe trigger checkout.session.completed
stripe trigger payment_intent.succeeded
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted
```

This is the fastest way to test webhook-handler code paths without running a real checkout.
