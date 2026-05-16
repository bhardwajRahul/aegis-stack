"""
Constants for the payment service.

Single source of truth for provider keys, transaction statuses, and event types.
"""


class ProviderKeys:
    """Payment provider identifiers."""

    STRIPE = "stripe"

    ALL = [STRIPE]


class TransactionStatus:
    """Transaction status values."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELED = "canceled"


class TransactionType:
    """Transaction type values."""

    CHARGE = "charge"
    REFUND = "refund"
    SUBSCRIPTION = "subscription"


class RefundReason:
    """Reason codes attached to a refund.

    The first three mirror Stripe's strictly-validated enum
    (``duplicate``, ``fraudulent``, ``requested_by_customer``) — any other
    value sent to Stripe's Refund API returns HTTP 400. We add ``OTHER``
    as a local-only sentinel for refunds that don't fit those buckets;
    it's stored on our transaction row but stripped before any provider
    call so the upstream API doesn't reject.

    When adding providers (Paddle, PayPal, etc.), each provider's refund
    method translates from this enum into its own accepted values.
    """

    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"
    OTHER = "other"

    ALL = [DUPLICATE, FRAUDULENT, REQUESTED_BY_CUSTOMER, OTHER]

    # Reasons the Stripe API actually accepts. OTHER is dropped before the
    # call; the user-facing label still lives on our transaction row.
    STRIPE_ACCEPTED = {DUPLICATE, FRAUDULENT, REQUESTED_BY_CUSTOMER}

    # Human-readable labels for the dashboard dropdown.
    LABELS = {
        DUPLICATE: "Duplicate charge",
        FRAUDULENT: "Fraudulent",
        REQUESTED_BY_CUSTOMER: "Requested by customer",
        OTHER: "Other",
    }

    DEFAULT = REQUESTED_BY_CUSTOMER


class PriceInterval:
    """Recurring billing interval for a price.

    Mirrors Stripe's ``recurring.interval`` enum exactly — these are the
    only four values Stripe's API emits. Enforced at the provider edge in
    ``StripeProvider.list_catalog`` so unknown values never propagate into
    the catalog cache or the dashboard.
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

    ALL = {DAY, WEEK, MONTH, YEAR}


class PriceType:
    """How a price is billed — one-time vs recurring."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"

    ALL = {ONE_TIME, RECURRING}


class SubscriptionStatus:
    """Subscription status values."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class WebhookEventType:
    """Stripe webhook event types we handle."""

    CHECKOUT_COMPLETED = "checkout.session.completed"
    PAYMENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_FAILED = "payment_intent.payment_failed"
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAYMENT_SUCCEEDED = "invoice.payment_succeeded"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    CHARGE_REFUNDED = "charge.refunded"

    # Fraud and disputes
    EARLY_FRAUD_WARNING_CREATED = "radar.early_fraud_warning.created"
    DISPUTE_CREATED = "charge.dispute.created"
    DISPUTE_UPDATED = "charge.dispute.updated"
    DISPUTE_CLOSED = "charge.dispute.closed"


class DisputeStatus:
    """PaymentDispute lifecycle states."""

    # Early fraud warning issued by the card network; chargeback may follow.
    WARNING_ISSUED = "warning_issued"
    # Warning was cleared (rare, but happens when the cardholder withdraws).
    WARNING_CLOSED = "warning_closed"
    # Actual chargeback filed; you have until `evidence_due_by` to respond.
    NEEDS_RESPONSE = "needs_response"
    # You submitted evidence; bank is deciding.
    UNDER_REVIEW = "under_review"
    # Closed in your favor.
    WON = "won"
    # Closed against you; funds returned to cardholder.
    LOST = "lost"
    # You preempted the chargeback with a refund before deciding.
    CHARGE_REFUNDED = "charge_refunded"

    ALL = [
        WARNING_ISSUED,
        WARNING_CLOSED,
        NEEDS_RESPONSE,
        UNDER_REVIEW,
        WON,
        LOST,
        CHARGE_REFUNDED,
    ]
    OPEN = [WARNING_ISSUED, NEEDS_RESPONSE, UNDER_REVIEW]


# Component name for health check registration
PAYMENT_COMPONENT_NAME = "payment"
