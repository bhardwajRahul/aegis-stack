# Research Brief: Personal-Finance Aggregator Schema

**Purpose:** Input to the schema design phase for a Plaid-backed aggregator (Empower/Quicken-class) added to the existing Python/SQLModel/Postgres app. Synthesized from Plaid API docs, Chase/AMEX connectivity, Quicken/OFX/CSV import formats, and four reference schemas (Firefly III, Actual Budget, Maybe Finance, GnuCash).

**Guiding constraints (from this codebase):** encrypt tokens with the existing AES-GCM helper; `owner_id` (+ nullable `organization_id`, org-tenancy port pending) on every user-scoped table; the pytest DB is SQLite with FK enforcement OFF, so DB-level FK/constraint behavior must be verified against live Postgres, not asserted in tests. The user explicitly does **not** want to add tables later — err toward shipping the full set now.

---

## 1. Connection model

Plaid's object hierarchy is **Item (one login at one institution) → Accounts → Transactions**. Model it, but make the connection layer **aggregator-polymorphic** (not Plaid-only) because of the 2025 JPMorgan-fee / CFPB-1033 uncertainty and the likely need for a Teller/SimpleFIN/manual fallback for AMEX.

**Per Item (connection), must store server-side:**
- `provider` (plaid | teller | simplefin | manual_import) + `provider_item_id` (Plaid `item_id`) — `item_id` is the stable per-connection key, **UNIQUE**. Linking the same bank twice = two Items.
- `access_token` — the secret, **encrypt at rest**, never exposed to client. Does not expire; revoked only via `/item/remove`.
- `institution_id`, `webhook_url`, `environment` ('sandbox' | 'production' — Items can't move between environments; **there is no 'development' env**, decommissioned 2024-06-20).
- `transactions_cursor` — the `/transactions/sync` `next_cursor`, stored **per Item**, opaque base64 ≤256 chars. This is the resumable ingestion pointer.
- `consent_expiration_time` — **NULLABLE**; usually null in US. **Do NOT hardcode a 90-day re-auth cadence** (that's an EU/PSD2 rule; Plaid explicitly calls the universal-90-day assumption a misconception). Each US institution sets its own policy. A successful Link update-mode run **resets** this value.
- Health/status fields (see below), `last_synced_at`, `created_at`, `updated_at`, `removed_at` (soft-delete for `/item/remove` teardown — critical because Transactions/Investments/Liabilities **bill monthly per Item** as long as a valid token exists).

**Connection health (separate from connection identity):** track `status` (healthy | login_required | pending_expiration | pending_disconnect | consent_expired | revoked | error), `last_error_code` (e.g. `ITEM_LOGIN_REQUIRED`, `OAUTH_CONSENT_EXPIRED`), `status_since`, `needs_user_action` (bool), `last_successful_sync_at`. Drive the "re-login" UI off `needs_user_action`, **not** raw error strings. Remediation is Link **update mode** (create a `link_token` from the existing `access_token`); the `access_token` stays the same after a successful update.

**Ephemeral tokens** (`link_token` ~4h / 30m in update mode, `public_token` 30m) are transient — keep them out of the durable connection row (or in a short-lived table). The durable secret is `access_token` + `item_id`.

**Chase/AMEX OAuth reality (institution capability flags matter):**
- **Both require bank-hosted OAuth** — no credential storage. You **must** register an allowlisted HTTPS `redirect_uri` in the Plaid dashboard and pass it in the `link_token`; **it cannot contain query params**. Chase supports app-to-app on mobile.
- **Chase returns Tokenized Account Numbers (TANs)** — the account/routing number is a token, not the real DDA. Store a `uses_tokenized_account_numbers` flag so nothing downstream treats it as a real routing number.
- **Capability asymmetry is real and must be a stored `supported_products` set:**
  - **Chase:** Auth, Balance, Transactions, Identity, **Liabilities**, Investments — fully supported.
  - **AMEX:** **Assets, Balance, Transactions ONLY.** No Liabilities, no Auth/Identity/Investments. So APR / statement-balance / minimum-payment / next-due-date columns will be **null for AMEX** and populated for Chase. AMEX charge cards also often have **no meaningful credit `limit`**. All liability/limit columns must be nullable and gated on `supported_products`.
- Treat **AMEX connection flakiness as a real operational risk** (reported "perpetual MFA"; possibly legacy-path artifact but design around it). This is the main argument for first-class **manual file import** as a fallback connection type.

**Webhooks:** an idempotent ingest log keyed by `item_id`. Key event is `TRANSACTIONS / SYNC_UPDATES_AVAILABLE` → enqueue a per-Item sync job (dedupe concurrent jobs per `item_id`). `ITEM / ERROR` (e.g. `ITEM_LOGIN_REQUIRED`), `PENDING_EXPIRATION` (~7 days out), `PENDING_DISCONNECT`, `USER_PERMISSION_REVOKED` flip `needs_user_action`.

**Sync loop invariant:** wrap the whole `has_more` loop **plus** the cursor advance in one DB transaction. Never persist a cursor for a batch you didn't fully apply — a mid-loop failure must re-run from the last committed cursor.

---

## 2. Transaction model

**Ledger decision (locked recommendation): single-entry** — one signed row per financial event on one account. This matches the Plaid/CSV/OFX import shape 1:1 (an importer gets ONE signed row + a balance, never the contra leg). Recover double-entry's two correctness wins with an explicit **transfers** link table and a **transaction_splits** child table. This mirrors Actual and Maybe. Strict GnuCash double-entry would force synthesizing a balancing "expense account" leg for every imported row — rejected.

**Money:** store as **integer minor units** (parity with Plaid amounts) OR `NUMERIC(19,4)` — **never float.** Recommend integer minor units + a per-currency `minor_unit_scale`. Flag this decision (§6).

**Sign convention — the sharp edge:** Plaid `amount` is **POSITIVE = outflow (money leaving), NEGATIVE = inflow.** OFX `TRNAMT` and Chase use accounting convention (**outflow negative**). AMEX CSV is the **inverse of Chase** (charges positive, payments negative). **Normalize sign to one canonical convention at ingest** (per-profile `amount_sign_convention` flag for CSV), and store the normalized signed amount. Pick one house rule and document it (recommend: outflow negative, matching OFX/accounting intuition).

**Canonical transaction fields (union of Plaid + OFX/QIF + CSV):**
- Identity/dedup: `provider_transaction_id` (Plaid `transaction_id` or OFX `FITID`), `import_hash` (content hash for id-less rows), `import_batch_id`.
- Money: `amount` (signed, normalized), `currency` (ISO 4217), `base_amount` + `base_currency` + `fx_rate` for reporting rollups.
- Dates: **`date` (posted/settled)** and **`authorized_date` (nullable — prefer for user-facing ordering)**; optional `datetime`/`authorized_datetime` timestamps.
- Descriptors: `original_description` (raw institution `name` / OFX `NAME`), `merchant_id` (Plaid-enriched `merchant_name`, normalized), `imported_payee`, `memo`/notes, `check_number`, `payment_channel` (online | in store | other).
- Category: **flatten Plaid PFC to `pfc_primary`, `pfc_detailed`, `pfc_confidence_level`** (raw capture) + a `category_id` FK to your own owned category tree (see §3). The legacy Plaid `category[]`/`category_id` is deprecated — do not model it as primary.
- Lifecycle: `status` (pending | posted), `pending` (bool), `pending_provider_id` (Plaid `pending_transaction_id`, self-referential — links the pending row to its posted successor).
- Structure/flags: `is_transfer`, `transfer_id`, `is_split` (→ `category_id` NULL when split), `recurring_stream_id`, `excluded_from_reports`, `cleared`, `reconciled`.
- Provenance: `raw_json` (JSONB) — **always persist the raw payload**. Future-proofs against new Plaid fields, lets you re-derive columns without re-fetching (avoids re-billing), and aids debugging.
- Nested-but-variable: `location` and `counterparties` as **JSONB** (don't explode into nullable columns).

**Dedup strategy (two-tier, this is the core correctness mechanism):**
1. **External-id path:** `UNIQUE(account_id, provider_transaction_id) WHERE provider_transaction_id IS NOT NULL` (partial). Covers Plaid `transaction_id` and OFX/QFX `FITID`. **FITID is unique only WITHIN an account at one institution — never globally**, so the key is the `(account_id, external_id)` tuple, never the id alone. Makes re-imports idempotent (`ON CONFLICT DO NOTHING/UPDATE`).
2. **Content-hash fallback** for id-less formats (**QIF and all CSV have no stable id**): `UNIQUE(account_id, import_hash) WHERE provider_transaction_id IS NULL` (partial). Hash over normalized `account_id + posted_date(ISO) + signed_amount_minor_units + normalized_payee + normalized_memo + check_number + within-day ordinal`. Normalize aggressively (uppercase, collapse whitespace, strip punctuation) before hashing.
3. **Cross-source reconciliation pass:** an id-less CSV/QIF row and a later Plaid row for the *same real transaction* would otherwise both land. On ingest of an id-less row (or a new Plaid row), fuzzy-match existing rows by `(account_id, date ±few days, exact amount, fuzzy payee)`; on a confident match, **MERGE** (attach the Plaid external-id/enrichment to the pre-existing imported row, mark reconciled) rather than insert. Store `dedup_status`/`source_precedence` so Plaid (authoritative) supersedes a hand-imported placeholder.

**Pending vs posted:** a pending txn and its posted counterpart have **DIFFERENT** `transaction_id`s; the posted row carries `pending_transaction_id`. Via `/transactions/sync` the pending row typically arrives in `removed[]` and the posted in `added[]`. Dedup on `transaction_id` alone double-counts — collapse via `pending_provider_id`.

**Transfers:** explicit `transfers` join table pairing the two legs (`from_transaction_id`/`to_transaction_id`, both `UNIQUE` so a leg belongs to one transfer only) + `is_transfer=true` on both legs so income/expense aggregations filter them out and net worth doesn't double-count. QIF encodes transfers as a bracketed `L[Account]` value — link to the counterpart account, **not** a category.

**Splits:** `transaction_splits` child table (`parent_transaction_id`, `amount`, `category_id`, `memo`, `sort_order`); app-enforced `SUM(splits.amount) = transaction.amount`, and parent `category_id` NULL when split (so reporting never double-counts). **Dedup/content-hash at the PARENT grain** so a multi-leg QIF transaction is one idempotent unit, not N. (Cleaner than Actual's self-referential parent/child rows because the money movement stays a single account row.)

---

## 3. Reference data

**Accounts taxonomy** — store `type`/`subtype` as **TEXT, not enum/CHECK** (Plaid adds new subtypes). Plaid top-level types: `depository | credit | loan | investment | other`, each with a large, growing subtype set (depository: checking/savings/hsa/cd/money market/…; investment: 401k/ira/roth/brokerage/hsa/529/crypto/…). Keep a normalized internal `account_type` for signing (checking, savings, credit_card, loan, investment, brokerage, crypto, property, vehicle, cash, other_asset, other_liability) plus `classification` (asset | liability) **stored** for fast net-worth signing. Balances group (`current`, `available`, `credit_limit`) all nullable. `UNIQUE(connection_id, provider_account_id)`. Keep `persistent_account_id` (stable across relinks) for reconnect reconciliation. `is_manual`, `is_on_budget`, `is_closed`, soft-delete.

**Categories — own the tree, seed from Plaid PFC (recommendation: adopt PFC as the seed, not the runtime authority):** self-referencing `categories` (`parent_id`, 2-level to mirror Plaid **primary/detailed**), with `plaid_primary`/`plaid_detailed` columns for auto-mapping incoming PFC, plus `classification` (income | expense | transfer), `is_system`, `is_hidden`. Seed the tree from Plaid's **16 primary + 104 detailed** PFC (published CSV; v2 default for integrations enabled on/after 2025-12-03) but own the table so users rename/hide/add without provider lock-in. Add a **`category_alias`/mapping** table so free-text category strings from QIF/Chase/AMEX map onto canonical ids; unmatched → 'uncategorized'. Preserve Quicken's orthogonal `/Class` axis as a separate **tags** table.

**Merchants/payees:** `merchants` with `owner_id` (NULL = global/provider-seeded), `name`, `normalized_name`, `source` (plaid | user | system | rule), `provider_merchant_id`, `logo_url`, `website_url`. `UNIQUE(owner_id, normalized_name)` for user merchants; `UNIQUE(source, provider_merchant_id)` for provider merchants. Keep the **raw description string on the transaction** separately so re-normalization is always possible.

**Currencies:** `currencies` (ISO 4217 code PK, name, symbol, `minor_unit_scale`). Seed USD. Every monetary column carries a currency FK — USD-only today shouldn't paint us into a corner. Plaid populates exactly one of `iso_currency_code` / `unofficial_currency_code` (crypto/non-standard) — capture both. `exchange_rates` (`from_currency`, `to_currency`, `rate_date`, `rate`; `UNIQUE(from, to, rate_date)`) for historical net-worth conversion.

**Securities:** shared/global `securities` (`ticker`, `name`, `security_type` equity/etf/mutual_fund/bond/option/crypto/cash/fixed_income/other, `exchange_mic`, `exchange_operating_mic`, `country_code`, `currency`, `provider_security_id`, `cusip`/`isin`/`sedol`). `UNIQUE(ticker, exchange_operating_mic)` case-insensitive; `UNIQUE(provider_security_id)` partial. Referenced by holdings AND trades (many accounts share one `security_id`).

**Import mapping (data-driven, not hardcoded parsers):** `import_profiles` (`header_signature` ordered column list for auto-detecting Chase-CC vs Chase-checking vs each AMEX CSV variant, `column_mapping` JSONB → canonical fields, `date_format`, `amount_sign_convention`, decimal/thousands handling). **Chase ships ≥2 layouts** (credit-card: Transaction Date/Post Date/Description/Category/Type/Amount/Memo; checking: Details/Posting Date/Description/Amount/Type/Balance/Check#). **AMEX ships multiple unversioned layouts** detected by column order, with inverted sign. Auto-select profile by matching the uploaded header row.

---

## 4. Investments & net-worth-over-time

Ship investment tables **now** even if launch is Transactions-only (see §6) — the user does not want a later migration, and investments are where the schema materially expands.

- **`securities`** — shared reference (above).
- **`security_prices`** — time series: `security_id`, `price_date`, `close_price`, `currency`. `UNIQUE(security_id, price_date, currency)`. Feeds market value.
- **`holdings`** — position snapshot per `(account_id, security_id, as_of_date)`: `quantity`, `cost_basis`, `average_cost`, `price`, `market_value`, `vested_quantity`, `currency`. `UNIQUE(account_id, security_id, as_of_date, currency)`. Holdings are **snapshots, not immutable events** — upsert, don't append. Current = latest date; historical rows feed the net-worth chart.
- **`trades`** (investment transactions — the security-movement event type): `account_id`, `transaction_id` (nullable link to the cash leg), `security_id`, `trade_type` (buy/sell/dividend/reinvest/transfer_in/transfer_out/fee/split), `trade_date`, `quantity`, `price`, `amount`, `fees`, `currency`, `provider_investment_transaction_id`. `UNIQUE(account_id, provider_investment_transaction_id)` partial. Plaid `/investments/transactions/get`.
- **`account_valuations`** — manual/anchor balance statements for illiquid or manually-tracked accounts (property, vehicle, crypto, cash) **and reconciliations**: `account_id`, `as_of_date`, `value`, `currency`, `source` (manual | reconciliation | provider). `UNIQUE(account_id, as_of_date)`. This is how non-transactional assets get on the net-worth chart and how you correct drift between imported balance and summed transactions.
- **`account_balances`** — **MATERIALIZED daily snapshot cache** (`account_id`, `balance_date`, `balance`, `cash_balance`, `holdings_value`, `currency`; `UNIQUE(account_id, balance_date, currency)`). Recomputed by a background job from transactions + valuations + holdings.

**Net-worth-over-time is a snapshot, NOT derived live.** Field standard across Maybe/Personal-Capital: one balance row per account per day, recomputed in a background job. Live derivation fails for imported accounts (you get current balance + a partial transaction window, never full history). Net-worth chart = `SELECT balance_date, SUM(balance) GROUP BY balance_date` against the cache. (Watch the worker-OOM history — keep the recompute job's per-request payloads bounded.)

**Liabilities** (Chase yes, AMEX no) — per-account detail refreshed on each pull (upsert, not append), keyed by `plaid_account_id`. Either one `liability_details` table + JSONB or three (`credit`/`mortgage`/`student`). Credit APRs are a nested array → child `credit_aprs(account_id, apr_type, apr_percentage, balance_subject_to_apr, interest_charge_amount)`. Store `next_payment_due_date`, `minimum_payment_amount`, `last_statement_balance`, `interest_rate` as typed columns (they drive UI) — all nullable, all gated on `supported_products` including liabilities.

**Recurring streams** (subscription / "wasting money" insights) — Plaid Recurring Transactions add-on (works best with ≥180 days history): `recurring_streams` with `merchant_id`, `category_id`, `direction` (inflow | outflow), `frequency`, `average_amount`, `last_amount`, `first_date`, `last_date`, `next_expected_date`, `status`, `is_subscription`, `provider_stream_id`. `transactions.recurring_stream_id` back-links occurrences. Fold user-scheduled bills (rent) in via a `source` flag rather than a separate schedules table.

---

## 5. Recommended table list (consolidated, ship all now)

**Connections & sync**
- `institutions` — aggregator-agnostic institution metadata + capability flags (`supported_products`, `oauth_required`, `uses_tokenized_account_numbers`, `uses_app_to_app`). `UNIQUE(provider, provider_institution_id)`.
- `connections` (Plaid Items) — one per institution login; encrypted `access_token`, `provider_item_id` (UNIQUE), `sync_cursor`, `environment`, `consent_expiration_time`, `removed_at`.
- `connection_status` — credential health separate from identity (status enum, `last_error_code`, `needs_user_action`, `last_successful_sync_at`). (May fold into `connections` if you prefer one row per connection.)
- `webhook_events` — idempotent webhook log keyed by `item_id` (`webhook_type`, `webhook_code`, `raw` JSONB, `received_at`, `processed_at`).

**Accounts & balances**
- `accounts` — one per provider account; type/subtype TEXT, classification, balances, `persistent_account_id`, `UNIQUE(connection_id, provider_account_id)`, soft-delete.
- `account_balances` — materialized daily net-worth snapshot cache.
- `account_valuations` — manual/anchor/reconciliation balance statements.
- `liability_details` (+ `credit_aprs` child, or JSONB) — per-account APR/statement/due-date detail, upserted per pull.

**Transactions**
- `transactions` — core single-entry ledger; two-tier dedup unique indices; `raw_json` JSONB.
- `transaction_splits` — parent/child category legs.
- `transaction_tags` — M2M `(transaction_id, tag_id)`.
- `transfers` — pairs the two legs of a transfer.
- `recurring_streams` — subscription/recurring insights.

**Investments**
- `securities` — shared security reference.
- `security_prices` — price time series.
- `holdings` — daily position snapshots (cost basis + market value).
- `trades` — investment/security-movement events.

**Reference data**
- `categories` — owned 2-level tree seeded from Plaid PFC, with `plaid_primary`/`plaid_detailed`.
- `category_aliases` — free-text → canonical category mapping.
- `merchants` — provider + user-scoped merchant/payee normalization.
- `tags` — Quicken `/Class` axis and user tags.
- `currencies` — ISO 4217 + minor-unit scale.
- `exchange_rates` — historical FX for base-currency rollups.

**Import & rules**
- `import_batches` (import runs) — one per uploaded file / sync run; `source_type`, `file_sha256`, counts, status, rollback unit.
- `import_batch_rows` (staging) — raw parsed record per row, `parsed_status`, `matched_transaction_id`, reason — powers review-before-commit + precise dup/error reporting.
- `import_profiles` — data-driven CSV/OFX column mappings + header signatures + sign convention.
- `rules` — data-driven auto-categorization / merchant assignment / transfer detection (`conditions` JSONB, `actions` JSONB, priority, enabled).

**Budgets & extras**
- `budgets` — period definition (`period_type`, `start_date`, `end_date`, currency).
- `budget_categories` — per-category budgeted amounts + `period_month` (YYYYMM) + `carryover_amount` + `goal_amount` (envelope budgeting never needs a new table).
- `attachments` — receipts/documents per transaction (ship now to avoid a later table).

**Cross-cutting:** every table gets `created_at`/`updated_at`, a soft-delete column (`deleted_at`), `owner_id`, and nullable `organization_id` (org-tenancy port pending).

---

## 6. Key decisions (with recommendations)

| Decision | Recommendation | Why |
|---|---|---|
| **Single vs double-entry** | **Single-entry** + `transfers` link table + `transaction_splits`. | Matches Plaid/CSV/OFX import shape 1:1; avoids synthesizing a contra leg per row; simpler queries. Mirrors Actual/Maybe. |
| **Money representation** | **Integer minor units** + per-currency `minor_unit_scale` in `currencies`. | Parity with Plaid amounts, exact arithmetic, no float drift. (`NUMERIC(19,4)` acceptable if cross-currency math simplicity is valued more.) |
| **Net-worth balances** | **Materialized daily snapshot** (`account_balances`), recomputed by a background job. | Live derivation fails for imported accounts (partial history); makes charting a trivial `GROUP BY date`. Keep recompute payloads bounded (OOM history). |
| **Plaid PFC adoption** | **Adopt as seed, own the runtime tree.** Store raw `pfc_primary`/`pfc_detailed`/`confidence` on the transaction AND map to owned `categories`. | Gets Plaid's 16/104 taxonomy for free without provider lock-in; users can rename/hide/add. |
| **Sign convention** | **Normalize at ingest to one house rule** (recommend outflow-negative); per-profile `amount_sign_convention` for CSV. | Plaid (outflow +), OFX/Chase (outflow −), AMEX (inverted) all disagree — normalize once, store signed. |
| **Dedup key** | **Two-tier:** `UNIQUE(account_id, provider_transaction_id)` partial + `UNIQUE(account_id, import_hash)` partial, plus a fuzzy cross-source merge pass. | FITID/Plaid-id idempotency where available; content-hash for QIF/CSV; merge prevents Plaid+manual double-landing. FITID is per-account-only, never global. |
| **Investments now or later** | **Build securities/prices/holdings/trades now**, even if launch is Transactions-only. | User forbids later table additions; investments are the biggest schema expansion. Gate *fetching* on enabled Plaid products, not on table existence. |
| **Aggregator coupling** | **Aggregator-polymorphic connection layer** (Plaid | teller | simplefin | manual). | 2025 JPMorgan fees + CFPB-1033 rewrite make Chase-via-Plaid cost/availability unsettled; AMEX flakiness needs a manual fallback. Swap providers without a schema rewrite. |
| **Manual import** | **First-class connection type**, not a side feature. | Only path with zero third-party dependency; guaranteed fallback (Chase CSV/QFX/QBO; AMEX CSV/QFX/OFX). |
| **Re-auth cadence** | **Store per-Item `consent_expiration_time` (nullable); never hardcode 90 days.** | 90-day is EU/PSD2, not universal US Plaid behavior; US institutions vary; update-mode resets it. |
| **Disconnect/teardown** | **Soft-delete + call `/item/remove` + record `removed_at`**; decide retention separately (open Q). | Subscription products bill monthly per live Item — must be able to stop billing while optionally retaining history. |
| **Splits/transfer invariants** | **Enforce in the application service layer** (splits sum to parent, transfer legs net to zero). | pytest DB is SQLite with FK OFF — DB-level CHECK/trigger behavior can't be asserted in tests; verify against live Postgres. |

**Unresolved product decisions to surface before/with schema design (don't block on them, but flag):**
- Which Plaid products at launch (Transactions only vs +Investments/+Liabilities) — drives per-Item subscription cost exposure, not table existence.
- Retention on disconnect: keep historical transactions or purge? (Affects FK-cascade vs soft-retain on `connections` delete.)
- Base currency & FX policy: single per-user base currency + snapshot `fx_rate` at txn time vs convert-on-read. Both need `exchange_rates`; changes whether `base_amount` is stored or computed.
- Cross-source merge aggressiveness: silently supersede a manual row with Plaid vs surface as a user-confirmable duplicate. Looser matching prevents dupes but risks merging two genuinely distinct same-day/same-amount transactions.
- Whether the cash side of a buy/sell shows in spending reports (link `trades.transaction_id` to a real cash-account row vs keep `trades` self-contained).
