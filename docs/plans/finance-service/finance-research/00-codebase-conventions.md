# aegis-pulse codebase conventions the finance schema MUST follow

**Stack:** SQLModel (>=0.0.14) on SQLAlchemy 2.0, Postgres (asyncpg async / psycopg2 sync). Alembic 1.16.5 migrations. FastAPI backend, taskiq+redis worker, APScheduler scheduler, Typer CLI. The generated finance template's tests run on in-memory SQLite with FK enforcement ON (via `PRAGMA foreign_keys=ON`), so FK/CHECK/partial-unique violations surface in unit tests; Postgres-only behavior (dedicated schemas, cross-schema FKs) still needs live-Postgres validation.

**Where models live:** per-service package `app/services/<svc>/models.py` bound to the single `SQLModel.metadata`. Finance goes in `app/services/finance/models.py`. New models MUST be imported in `alembic/env.py`'s import block or they won't be seen by autogenerate.

**Primary keys:** `id: int | None = Field(default=None, primary_key=True)` — integer autoincrement. NO UUIDs anywhere. Composite PKs only for pure join tables (`(a_id, b_id)`).

**Timestamps:** NO shared mixin. Each model inlines naive-UTC columns via a helper:
```python
def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
created_at: datetime = Field(default_factory=utcnow_naive)
updated_at: datetime = Field(default_factory=utcnow_naive)
```
Naive UTC is deliberate (SQLite/Postgres portability). Soft-delete: `deleted_at: datetime | None = Field(default=None, index=True)` + a partial unique index that excludes soft-deleted rows.

**Money:** integer smallest-currency-unit (cents), NOT Decimal/float. `amount: int` + `currency: str = Field(max_length=3, default="usd")`. There is ZERO Decimal/Numeric money usage in the codebase — match this. (Aggregate fields named like `total_x_cents: int`.)

**Enums:** stored as `String` + a `CheckConstraint`, NEVER native PG enum (SQLite parity + "adding a value is a normal migration"). Idiom:
```python
class BlogStatus(StrEnum): DRAFT="draft"; PUBLISHED="published"; ARCHIVED="archived"
status: BlogStatus = Field(default=BlogStatus.DRAFT,
    sa_column=Column("status", String(16), nullable=False, index=True))
__table_args__ = (CheckConstraint("status IN ('draft','published','archived')", name="ck_blog_post_status"),)
```
NOTE: for taxonomies Plaid keeps EXPANDING (account type/subtype, PFC), store as plain TEXT with NO check constraint — only use CheckConstraint for small closed sets we own (status/direction/classification/source).

**FKs:** simple form `field: int = Field(foreign_key="other.id", index=True)` — EVERY FK indexed. When ON DELETE / use_alter needed, drop to raw Column with a NAMED ForeignKey:
```python
sa_column=Column("x_id", Integer, ForeignKey("other.id", name="fk_thistable_x_id", ondelete="SET NULL", use_alter=True), nullable=True)
```

**Indices / constraints in `__table_args__`:** composite/partial via `sqlalchemy.Index("ix_<table>_<cols>", ...)`; unique tuples via `UniqueConstraint(..., name="uq_<...>")`; checks via `CheckConstraint(..., name="ck_<table>_<col>")`. Partial unique indices use `postgresql_where=` (verified only on live PG).

**Naming:** explicit `__tablename__` = singular snake_case (`payment_transaction`, `blog_post`). Columns snake_case. Index `ix_<table>_<col>`, unique `uq_...`, check `ck_...`, fk `fk_...`. `metadata` is reserved by SQLModel → use Python attr `metadata_` mapped to DB column `"metadata"`.

**JSON:** `col: dict[str, Any] = Field(default_factory=dict, sa_column=Column("col", JSON))`; nullable JSON lists via `sa_column=Column(JSON, nullable=True)`. Use JSON/JSONB for raw provider payloads and variable nested data (location, counterparties) — do NOT explode into nullable columns.

**Ownership / tenancy:** every user-scoped row carries `owner_user_id: int = Field(foreign_key="user.id", index=True)` and a nullable `organization_id: int | None = Field(default=None, foreign_key="organization.id", index=True)` (org infra exists but is NOT active yet — reads are owner-based; include the column now, don't depend on it).

**Encrypted secrets:** AES-256-GCM via `app.core.encryption.encrypt_secret(plaintext, *, context=...)` / `decrypt_secret(..., context=...)`. Ciphertext stored in a plain `str` column; encrypt/decrypt happen in the SERVICE layer, not the model. The AAD `context` binds ciphertext to its row, e.g. `f"plaid_connection:{id}:access_token"`. Add any new encrypted-column table to the key-rotation CLI `app/cli/security.py::_run`. Model `__repr__` should mask secret columns.

**Service pattern:** `class FinanceService: def __init__(self, db: AsyncSession) -> None: self.db = db`. Queries via `sqlmodel.select` + `await self.db.exec(...)`. Writes call `self.db.add(...)` + `await self.db.flush()` — services do NOT commit; the request-scoped `get_async_db` dependency commits. Per-service `deps.py`: `async def get_finance_service(db: AsyncSession = Depends(get_async_db)) -> FinanceService: return FinanceService(db)`.

**Idempotent UPSERT (the dedup mechanism):** Postgres `insert(Model).values(...).on_conflict_do_update(index_elements=[...], set_={...})` (or `on_conflict_do_nothing`) keyed on the natural UNIQUE key — this is how existing ingest (pypi_daily) dedups. Every dedup unique key must be a real UNIQUE constraint/partial-unique index.

**Migration:** declared as a `ServiceMigrationSpec` in `aegis/core/migration_generator.py` and rendered into an `alembic/versions/00X_<service>.py` file with an **auto-assigned** revision ID (e.g. `001_finance.py`) so the chain is valid for any `include_*` combination; a reversible `downgrade()` is generated unless the spec is explicitly forward-only. Do NOT hand-write revision IDs/filenames.

**Reuse note:** the existing `app/services/insights/` service already ships `insight_source`, `insight_record`, `insight_event`, `goal` tables and a rule-based anomaly-event system (country-spike events). "Wasting money" insights can emit `insight_event`-style rows (rule-based, ships without AI) AND/OR feed the future Illiana AI layer (a `finance_context.py` provider). The AI layer (Illiana) is NOT in this project yet (`include_ai: false`) — design finance data to be AI-ready but don't depend on Illiana existing.
