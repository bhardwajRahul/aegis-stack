"""Finance service constants: provider keys, ciphertext column registry.

Enum-style value sets that back ``String`` + ``CheckConstraint`` columns are
added here as their tables land. Kept as plain string constants (not native
DB enums) so adding a value is a normal migration on both SQLite and Postgres.
"""

SERVICE_NAME = "finance"


class Provider:
    """Connection providers. ``manual`` always ships; the rest are flag-gated."""

    PLAID = "plaid"
    SNAPTRADE = "snaptrade"
    MANUAL = "manual"


# Encrypted (AES-GCM ciphertext) columns on ``finance_connection``. Registered
# here so key-rotation tooling can find every finance secret. Encryption /
# decryption happens in the service layer with a row-bound AAD context
# ``finance_connection:{id}:{column}``.
ENCRYPTED_COLUMNS: tuple[str, ...] = (
    "access_token_encrypted",
    "api_key_encrypted",
    "api_secret_encrypted",
    "api_passphrase_encrypted",
    "refresh_token_encrypted",
)
