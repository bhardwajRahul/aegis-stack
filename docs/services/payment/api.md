# API Reference

Complete REST API documentation for the Payment Service.

## Base URL

All endpoints are prefixed with `/api/v1/payment`.

## Authentication

If the auth service is enabled in your project, all endpoints except `POST /webhook` require an authenticated user (via `get_current_active_user` dependency). The webhook endpoint is always unauthenticated; Stripe authenticates itself via signature verification.

### Per-user scoping (auth-only)

When auth is included, the authenticated user's ID is forwarded to every query and mutation, giving row-level isolation:

- `GET /transactions`, `GET /subscriptions`, `GET /disputes` return only rows tied to the current user's `PaymentCustomer`.
- `GET /transactions/{id}`, `GET /disputes/{id}` return `404` for rows owned by another user (indistinguishable from a missing row on purpose).
- `POST /refund/{id}` and `POST /subscriptions/{id}/cancel` return `404` for rows owned by another user, users can't refund or cancel each other's payments.
- `POST /checkout` upserts a `PaymentCustomer` for the authenticated user on first use, then reuses the `provider_customer_id` on every subsequent checkout so Stripe sees one customer per app user.

### Anonymous flow (no auth)

When auth is **not** included, all endpoints are open (no dependency) and no per-user scoping is applied. Useful for public payment flows: donations, guest checkouts, pre-signup trials. Stripe creates a fresh customer at checkout time from the email the user enters on the hosted page; the webhook handler backfills a `PaymentCustomer` row with `user_id=NULL`.

## Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/payment/checkout` | Create checkout session |
| `GET` | `/api/v1/payment/transactions` | List transactions (paginated) |
| `GET` | `/api/v1/payment/transactions/{id}` | Get single transaction |
| `POST` | `/api/v1/payment/refund/{id}` | Refund a transaction |
| `GET` | `/api/v1/payment/subscriptions` | List subscriptions |
| `POST` | `/api/v1/payment/subscriptions/{id}/cancel` | Cancel subscription |
| `GET` | `/api/v1/payment/disputes` | List disputes and early fraud warnings |
| `GET` | `/api/v1/payment/disputes/{id}` | Get single dispute |
| `GET` | `/api/v1/payment/status` | Service status overview |
| `POST` | `/api/v1/payment/webhook` | Webhook ingress (no auth) |

## Checkout

### Create Checkout Session

Redirects users to Stripe's hosted checkout page for payment collection.

```http
POST /api/v1/payment/checkout
```

**Request Body**

```json
{
  "price_id": "price_1TNMKUBdyuVC9MXv9KeFBOEA",
  "quantity": 1,
  "mode": "payment",
  "success_url": "http://localhost:8000/payment/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "http://localhost:8000/payment/cancel"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `price_id` | `string` | Yes | Stripe Price ID (`price_...`) |
| `quantity` | `integer` | No | Quantity (default `1`) |
| `mode` | `string` | Yes | `"payment"` (one-off) or `"subscription"` (recurring) |
| `success_url` | `string` | No | Redirect target on successful payment. Include the `{CHECKOUT_SESSION_ID}` placeholder if you want to look up the session server-side after redirect. Falls back to `PAYMENT_SUCCESS_URL` setting, then to the bundled page at `/payment/success`. |
| `cancel_url` | `string` | No | Redirect target if the user aborts. Falls back to `PAYMENT_CANCEL_URL` setting, then to the bundled page at `/payment/cancel`. |

!!! tip "Fallback chain"
    Resolution order: request body field → `PAYMENT_*_URL` settings → built-in default routes. A generated project can do end-to-end checkout with just `price_id` and `mode` because the service ships with styled default landing pages.

**Response (200)**

```json
{
  "session_id": "cs_test_a1DTAIpflXQxc2VNPC...",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "provider_key": "stripe"
}
```

**Error Responses**

| Status | Cause |
|--------|-------|
| `400` | Stripe rejected the request (invalid price, mode/price mismatch, etc.). `detail` contains Stripe's user-facing message. |
| `400` | Card declined during checkout creation (rare at this step). |
| `401` | `STRIPE_SECRET_KEY` is invalid or revoked. |

## Transactions

### List Transactions

```http
GET /api/v1/payment/transactions?page=1&page_size=20&status=succeeded
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | `1` | Page number (1-indexed) |
| `page_size` | `integer` | `20` | Results per page |
| `status` | `string` | (none) | Filter: `succeeded`, `pending`, `failed`, `refunded`, `partially_refunded`, `canceled` |

**Response (200)**

```json
{
  "transactions": [
    {
      "id": 42,
      "provider_transaction_id": "pi_3ABC...",
      "type": "charge",
      "status": "succeeded",
      "amount": 12000,
      "currency": "usd",
      "description": "Premium plan April 2026",
      "created_at": "2026-04-17T14:22:03Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

Amounts are in the currency's smallest unit (cents for USD). Divide by 100 for display.

### Get Single Transaction

```http
GET /api/v1/payment/transactions/{id}
```

Returns a single `TransactionResponse` (same shape as list items). Returns `404` if the ID doesn't exist.

## Refunds

### Refund a Transaction

Issue a full or partial refund against a previous charge.

```http
POST /api/v1/payment/refund/{transaction_id}
```

**Request Body**

```json
{
  "amount": 5000,
  "reason": "requested_by_customer"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | `integer` | No | Partial refund amount in cents. Omit for a full refund. |
| `reason` | `string` | No | `requested_by_customer`, `duplicate`, `fraudulent`, or an arbitrary note |

**Response (200)**: returns the new refund `TransactionResponse` (a separate record, `type: "refund"`) linked to the original charge.

Returns `404` if the transaction ID doesn't exist.

## Subscriptions

### List Subscriptions

```http
GET /api/v1/payment/subscriptions?status=active
```

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | `string` | Filter: `active`, `past_due`, `canceled`, `incomplete`, `trialing`, `unpaid` |

**Response (200)**

```json
{
  "subscriptions": [
    {
      "id": 7,
      "provider_subscription_id": "sub_1ABC...",
      "plan_name": "Premium",
      "status": "active",
      "current_period_start": "2026-04-01T00:00:00Z",
      "current_period_end": "2026-05-01T00:00:00Z",
      "cancel_at_period_end": false
    }
  ],
  "total": 1
}
```

### Cancel Subscription

Schedules cancellation at the end of the current billing period. The subscription remains active until `current_period_end`; Stripe will then stop billing.

```http
POST /api/v1/payment/subscriptions/{id}/cancel
```

**Response (200)**

```json
{
  "status": "canceled",
  "cancel_at_period_end": "true"
}
```

Returns `404` if the subscription ID doesn't exist.

## Disputes

### List Disputes

```http
GET /api/v1/payment/disputes?status=open
```

Returns early fraud warnings (EFWs) and chargebacks recorded by the webhook handler.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | `string` | `open` for disputes needing attention (warning_issued, needs_response, under_review), or any specific status: `warning_issued`, `warning_closed`, `needs_response`, `under_review`, `won`, `lost`, `charge_refunded` |

**Response (200)**

```json
{
  "disputes": [
    {
      "id": 1,
      "transaction_id": 42,
      "provider_dispute_id": "dp_test_abc",
      "status": "needs_response",
      "reason": "fraudulent",
      "amount": 5000,
      "currency": "usd",
      "evidence_due_by": "2026-05-02T00:00:00Z",
      "event_type": "charge.dispute.created",
      "created_at": "2026-04-18T14:22:03Z",
      "updated_at": "2026-04-18T14:22:03Z"
    }
  ],
  "total": 1
}
```

### Get Single Dispute

```http
GET /api/v1/payment/disputes/{id}
```

Returns a single `DisputeResponse`. `404` if the id doesn't exist.

## Status

### Service Status Overview

```http
GET /api/v1/payment/status
```

Returns a compact summary of provider health and aggregate metrics. This powers the dashboard Payment card and the `my-app payment status` CLI command.

**Response (200)**

```json
{
  "provider": "stripe",
  "enabled": true,
  "is_test_mode": true,
  "total_transactions": 12,
  "total_revenue_cents": 124000,
  "active_subscriptions": 3
}
```

## Webhook

### Webhook Ingress

```http
POST /api/v1/payment/webhook
```

**No authentication**. Stripe authenticates via the `Stripe-Signature` header, which the service verifies using `STRIPE_WEBHOOK_SECRET`. Unauthenticated requests or requests with invalid signatures return `400 Invalid payload`.

This endpoint handles (persists to the database as appropriate):

- `checkout.session.completed`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `invoice.paid`
- `invoice.payment_failed`
- `customer.subscription.created` / `.updated` / `.deleted`
- `charge.refunded`
- `radar.early_fraud_warning.created` (writes a `PaymentDispute` row with status `warning_issued`)
- `charge.dispute.created` / `.updated` / `.closed` (upserts a `PaymentDispute` row; status maps Stripe's `needs_response` / `under_review` / `won` / `lost` / `charge_refunded` to our lifecycle)

**Response (200)**

```json
{ "received": "true" }
```

Unrecognized event types are acknowledged but not persisted. Point Stripe at this URL from your dashboard (production) or via `my-app payment webhook` / `stripe listen` (local).

## Error Response Format

FastAPI returns errors in standard format:

```json
{
  "detail": "Human-readable error message"
}
```

For `400` errors caused by Stripe rejecting the upstream request, `detail` is Stripe's `user_message` (friendly text), e.g. `"You specified 'payment' mode but passed a recurring price."`
