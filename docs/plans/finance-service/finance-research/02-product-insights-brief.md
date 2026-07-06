# Product Insights & Hard-Won Lessons
### A field brief for building your first personal-finance aggregator (Plaid + Quicken import, Chase/AMEX, "wasting money" insights)

---

## 0. The one-paragraph orientation

You are building three products stapled together: a **net-worth tracker** (a *snapshot/persistence* problem, not a math problem), a **transaction ledger + importer** (a *dedup and mutability* problem), and an **insight engine** (a *merchant-normalization* problem before it is an *AI* problem). The headline features are all trivial arithmetic; every ounce of difficulty is in the plumbing beneath them — history you had to be capturing since day one, IDs that aren't stable, signs that flip per source, and a bank that silently edits the past. Get the schema right first, because almost every hard bug here is a schema decision you can't retrofit.

---

## 1. Feature landscape — table stakes vs differentiators

| Category | Table stakes (users leave if missing) | Differentiators (what people pay for) | Where the real work hides |
|---|---|---|---|
| **Net-worth tracking** | Net-worth-over-time line = Σ(assets) − Σ(liabilities); linked + **manual** accounts; per-account drill-down | Investment Checkup / allocation analysis across *all* accounts; fee analyzer; "You Index" vs S&P; Zillow/depreciation valuation of manual assets; IRR on illiquid assets | The trend line is **stored snapshots**, not recomputed math. If you didn't snapshot from day one, history is *unrecoverable*. |
| **Budgeting** | Categorized transactions; budget-vs-actual; monthly rollup | Philosophy (YNAB zero-based envelopes vs Monarch flex-buckets vs Simplifi top-down "available to spend"); anomaly-vs-*your-own*-baseline alerts; cash-flow forecast | Two different "overspending" surfaces: budget-vs-actual (a ledger compare) **and** anomaly-vs-baseline (needs rolling 3/6/12-mo averages). |
| **Subscription / "wasting money"** | Detected recurring list; upcoming bills; price-change alerts | Duplicate-service detection; free-trial-converted; forgotten-annual; fee/interest detection; **bill negotiation/cancellation** (the actual revenue) | Every insight is a *cheap SQL query* over one good `recurring_series` table. The table is the whole game. |
| **Investments** | Holdings list; current value; allocation pie | Cost basis / tax lots; Form 8949; capital-gains estimator; TWR vs IRR performance | Accurate lots need **full transaction history + corporate actions** — data aggregators don't reliably give you. This is a separate, harder tier. |
| **Connectivity** | Auto-sync of transactions + balances; manual file import | Broad institution coverage; reconnection UX; multi-currency | Aggregation is a **permanent maintenance tax**, not a one-time integration. Model connection *health* as a first-class entity. |

**Opinion:** For a v1 solo build, ship *net-worth + categorized cash-flow + subscription insights* and treat *tax-grade cost basis* as an explicit non-goal (label it "approximate"). Sharesight/Quicken exist because that tier is a product unto itself.

---

## 2. Things you probably don't know (highest-value non-obvious insights)

**1. Credit-card-payment double-counting is the #1 credibility bug.** A $500 card payment appears **twice**: an outflow on checking and an inflow on the card. Naively summing outflows counts the $500 payment *on top of* the $500 of purchases it paid off — Mint was infamous for reporting ~2× real annual spending. Fix: detect + pair both legs, tag a shared `transfer_group_id`, exclude both from cash-flow/income. **Net worth is immune** (one account down, one liability down, cancels) — only spending/income totals get wrecked.

**2. "Is this a transfer" is genuinely hard, not an equal-and-opposite match.** Amounts differ (partial payments, a $2 fee, FX); legs land days apart or across a sync boundary; two unrelated $50 charges create false positives; you may only have *one* side linked (then it *is* real spending — don't hide it); and Venmo-to-a-friend looks identical to an internal move but is real cash-flow out. Build a **confidence score** (amount closeness + date proximity + provider category + recurring counterparty), require *both* accounts to belong to the same user before auto-hiding, and **suggest-and-confirm** below a high threshold rather than silently zeroing money.

**3. Pending → posted is a DELETE + INSERT, not an update.** Plaid *removes* the pending row and *inserts* a new posted row with a **different** `transaction_id`, linked only by `pending_transaction_id`. Amounts change (restaurant pending *without* tip → posts *with* tip) and dates move 1–5 (up to 14) days. If you key dedup on amount+date+name, the tip breaks it and you show the coffee twice. Key on the stable provider id + the pending linkage.

**4. Phantom pendings never post.** Gas $1/$100 pre-auths, hotel/rental deposits, voided charges show up pending then just *drop off* (Plaid `removed` array) — funds released, no posted counterpart. Never build durable history (net-worth snapshots, budget actuals) on pending rows or you manufacture spending that never happened.

**5. Your store cannot be append-only-immutable — the bank edits the past.** Banks retroactively fix descriptions/amounts/categories and **delete** transactions (fraud reversals). Plaid ships this as `modified` and `removed` arrays against a persisted **sync cursor**. Engineers instinctively reach for event-sourcing and then can't apply edits, so balances drift permanently and deleted fraud stays visible forever. Model transactions as **mutable upserts + soft-delete**; put any audit need in a *separate* changelog table.

**6. Sign conventions are inverted and flip per source.** Plaid: **positive = money OUT** (counterintuitive), and it *inverts again* for investment accounts (a sale is negative). OFX/QFX: trust the `TRNAMT` **sign**, not the `TRNTYPE` label — and many banks (Capital One, BofA cards) ship the sign *reversed* so charges import as payments. CSV is chaos (signed col vs separate debit/credit cols). Normalize to **one documented internal convention** at ingest, store `raw_amount` + `signed_amount`, and unit-test every importer with a known debit and known credit.

**7. Manual assets ARE net worth, and they're structurally identical to synced accounts.** A house, car, private company, collectibles are never aggregatable but are a huge share of true wealth. For the net-worth chart, both a synced account and a manual asset reduce to "a dated value" — unify them into one value-history time series (`source = sync|manual`). Manual assets add a **staleness** concept (nobody re-values their house), so add `last_valued_at` + `is_stale` + `stale_after_days`.

**8. Net-worth-over-time is a persistence problem you can't retrofit.** Aggregators hand you a *current* balance, never history; Plaid's transaction lookback wall (default 90d, initial ~30d, max 730d, capped by the institution) means you *cannot* walk backward to reconstruct it. The only way to get a real trend is a **scheduled snapshot job** writing one balance row per account per day starting at link time — independent of whether the user ever opens the app. This is the single most consequential, most easily-missed decision in the whole app.

**9. Balance ≠ Σ(transactions), ever.** You only fetched N days; pending affects available-vs-current differently; the bank has a starting point you never saw. **Trust the provider's reported balance as authoritative**; if you need a running balance, seed a synthetic **starting-balance/adjustment entry** = `reported_balance − Σ(known_txns)`. New builders assume balance = running sum and then can't explain a $400 disagreement with the bank.

**10. Connection breakage is the steady-state, not an incident.** MFA re-auth breaks on nearly every login for some users; institutions rotate APIs; accounts get stuck "loading"; transactions live in permanent pending limbo. Chase specifically is *flaky on Plaid* and needs frequent re-auth. Surface **reauth as a product state** (`needs_reauth`), and on a failed sync **carry forward last-known balance** rather than dropping the account and cratering the net-worth line.

**11. Subscription "unused" detection is a euphemism you must not over-promise.** Bank data *cannot* see whether you use Netflix. Rocket Money's "inactive" list is really "a known recurring series that stopped charging." "Unused" just presents *all* detected subscriptions and lets the human decide. And recurring detection is a **merchant-normalization problem before it's ML** — feed raw bank descriptions into cadence clustering and the same service shows up as 3 merchants and never clusters. You need ≥3 occurrences to confirm a series (so annual charges are invisible for a year → model a *confidence/maturity* field, not a boolean), you must actively *exclude* habitual spend (groceries/gas/coffee/Amazon), and variable bills (utilities) need an `is_variable` flag + tolerance band or they false-positive on both detection *and* price-hike alerts.

**12. The Mint shutdown is a spec, not trivia.** Mint died Nov 2023 because free ad/referral monetization on a budgeting app is structurally weak. Intuit migrated users to Credit Karma and carried over **none** of their history, custom categories, budgets, goals, or recurring labels — a one-way, irreversible strand. The exodus (Monarch/YNAB/Copilot/Rocket Money — all *subscription*-priced) was driven by people with years of data trapped. Lessons: **(a)** decide monetization before schema (funnel vs subscription changes what you optimize); **(b)** treat the user's history/categories/rules as **theirs from day one** — build export/import early; **(c)** historical snapshots are user data you can *never regenerate* — treat them as append-only and sacred (acquisition rewrites like Empower's caused literal data loss).

**13. The Plaid access/cost reality for a solo dev.** Plaid's "free tier" is a **demo, not a runway**: ~10 Production Items and ~200 live calls *per product*, and **failed calls also burn quota** — so one flaky Chase reconnect silently drains it. Beyond that it's pay-as-you-go (~$0.10–0.60/call), Growth needs a 12-month commit, Enterprise is $1k–10k+/mo, and full production requires a business-use-case *approval* a hobby project won't clear. Prior art: **Maybe Finance (funded team) explicitly refused to ship self-hosted Plaid**, citing OAuth complexity + pricing + per-user cost — telling self-hosters to bring their own keys. That is a strong signal *against* Plaid-first.

**14. IRR vs TWR is a schema fork you pick before any UI.** Money-weighted IRR needs *dated cash flows*; time-weighted return needs *period balances*. Illiquid/manual assets → IRR; index comparison → TWR. And performance numbers **never match the brokerage** — Empower's "You Index" is current holdings "extrapolated backward," an *approximation*, precisely because true return needs clean dated cash flows aggregators don't deliver. This is expectation-management, not a math bug — label it approximate in the UI.

**15. Cross-source dedup has no shared ID.** Plaid `transaction_id` and OFX `FITID` are *per-source*. Re-linking a broken bank mints a **new Plaid Item → new ids for the same history**, so a naive sync duplicates everything. Within a source, dedup on the stable id; across sources you have only fuzzy signals (account + amount + date window + normalized payee) — **suggest a merge, let the user confirm**, never destructively auto-collapse.

---

## 3. Connectivity recommendation

**Verdict: file-import-first, with a pluggable multi-provider sync layer bolted on. Do NOT be Plaid-first.**

The reasoning, specific to *Chase + AMEX*:

- **Direct OFX / bill-pay is dead for your two banks.** Direct Connect (the only two-way, bill-pay method) is gone: Chase migrated everything to download-only EWC+; AMEX dropped OFX entirely (~Aug 2024). Chase killed raw OFX Direct Connect in Oct 2022; AMEX's endpoint returns 403/503. Self-hosted `ofxtools` for Chase requires a per-device `CLIENTUID` + a secure-message-link + SMS/email code within a 7-day window, and many banks 403 anything not impersonating "Quicken for Windows." **Treat OFX Direct Connect as an at-most best-effort power-user importer, never a backbone.**
- **Enterprise aggregators (MX/Finicity/Akoya) are unobtainable solo** — all sales-led with signed data-recipient agreements. They're future plug-in slots only.
- **The EU "free open-banking" everyone recommends (Nordigen/GoCardless) is closed to new signups (mid-2025) and never covered US banks.** Irrelevant to you.

**Recommended provider ladder for a US solo dev wanting Chase + AMEX:**

1. **Manual/file import (CSV / OFX / QFX / QIF)** — the guaranteed, zero-approval, privacy-preserving *floor*. Build this excellently first; it's also your Quicken-migration path (see below).
2. **SimpleFIN Bridge (~$15/yr)** — the cheapest real auto-sync obtainable with **zero approval**. Read-only, credentials never touch your server (a single-use token → long-lived Access URL; MX holds the bank relationship). Covers Chase/AMEX. Tradeoff: ~once-daily refresh, ~90 days history. **This is your best default auto-sync.**
3. **Teller.io (100 free live US connections)** — richer/real-time, self-serve, covers Chase/BofA/Citi/Cap One/AMEX. But it's reverse-engineered against banks' mobile APIs + requires **mTLS client certs**, so it *breaks* when a bank changes behavior — never your only path.
4. **Plaid as an optional bring-your-own-keys premium provider** — mirror exactly what Maybe Finance did. Don't make your product depend on it.

**Quicken import surface (Chase/AMEX users migrating off Quicken):** you will *never* parse the `.QDF` (undocumented OLE compound file behind paid software). The real artifacts are **QFX/OFX > CSV > QIF**, ranked by fidelity. QFX carries `FITID` (real dedup key) + balances + cleared status; QIF is officially lossy (drops lots, tax lines, reminders, memorized payees, budgets, often correct balances, and has *no* stable id so it duplicates on re-import). Ignore the `INTU.BID` header (it only gates files to a paid Quicken subscription). Document that the user must run Quicken's own Export first.

**The fallback path (always present):** every provider adapter emits into one **normalized internal transaction shape**; if a live provider breaks, the user drops back to file import with zero data-model change. Manual file-import-only is also a genuine **privacy differentiator** — a real segment of users refuses aggregators outright.

---

## 4. "Wasting money" insight playbook

Every insight below is a *specific query* over `recurring_series` + `transactions` + `spending_baselines` — not AI magic. The engine's value is in the tables; the "AI" is mostly the merchant-normalization + per-user categorization model underneath.

| Insight | Detectable signal | Data it needs | Gotchas |
|---|---|---|---|
| **Recurring / subscription detection** | Group txns into a "stream" when normalized merchant + amount + cadence align; ≥3 occurrences = "mature," 1–2 = "early_detection" | Normalized `merchant_id`; cadence bucket; `occurrence_count`; `confidence/status` | Merchant normalization first. **Exclude** groceries/gas/coffee/Amazon or the list fills with false positives. |
| **Price-hike** | `last_amount` materially > running/expected `avg_amount` on the same series | `expected_amount` + `last_amount` per series; a **tolerance band** | Variable bills (utilities) must be flagged `is_variable` or they false-alarm every cycle. |
| **Unused / inactive subscription** | A known series with **no charge in the last cadence window** (that's all bank data can prove) | `next_expected_date`, `last_charge_date`, cadence | You *cannot* detect actual usage. Frame as "here are all your subscriptions, you decide." |
| **Duplicate services** | >1 *active* series in the same **service category** (Spotify + Apple Music) | merchant → `service_type` taxonomy (music/video/gym…) on top of merchant matching | Needs a service-type layer; merchant match alone won't catch two different merchants. |
| **Free-trial-converted / forgotten annual** | First real charge after a $0/trial pattern; a single large annual charge on a mature-but-sparse cadence | series history + occurrence dates | Annual charges are invisible until the 3rd year — use `early_detection` to surface probable ones sooner. |
| **Fee / interest detection** | Category/merchant match on overdraft, interest, late-fee, foreign-transaction-fee lines | category taxonomy incl. fee categories | FX fees arrive as their *own* separate line days after the foreign charge. |
| **Category overspend (budget-vs-actual)** | Category actual > allocated for the period | `category_budgets` (allocated per period) | Distinct from anomaly detection below. |
| **Spending anomaly (vs your own baseline)** | This month's category (or merchant) spend is X% above your trailing 3/6/12-mo average | `spending_baselines` (rolled trailing averages) | This is what "you're wasting money" usually *means*; most naive builds lack the baseline entirely. Simplifi uses a 12-mo average. |
| **Low-yield cash** | Large balance sitting in a checking/low-APY account | account balances + account type + a reference APY | Actionable, high-trust, and free once you have balances. |

**Categorization precedence is a hard contract, not an implementation detail:** `provider/base category` → `per-user ML prediction (suppressed if low-confidence)` → `deterministic user rules (highest priority, always win)`. Run auto-categorization *before* user rules. Get this backwards and user corrections get silently overwritten — a trust-killer. Use a **per-user** model (Copilot's approach — "AMZN" is groceries for one person, business supplies for another), with a cold-start fallback to the provider category until ~30 reviewed transactions exist, and a corrections store that feeds *only* that user's model.

**Rules engine to copy (Lunch Money):** conditions on payee (contains/starts/exact), notes, category, amount type (debit/credit), amount range (between/>/</=), day-of-month range (with wrap), account; actions set payee/notes/category, add tags, link recurring, split, mark reviewed, notify, delete (one-off only); **priority-ordered**; and setting up a recurring item **auto-spawns a matching rule** so future transactions auto-link.

**Free bonus:** cash-flow forecasting is nearly free once `recurring_series` has `next_expected_date` + `expected_amount`: `projected_balance(t) = current_balance + Σ(expected inflows ≤ t) − Σ(expected outflows ≤ t) − planned_spend`. Same table that powers subscription detection. Allow a **few-days tolerance** on `next_expected_date` or date-drift ("monthly" landing on the 1st, then 3rd, then 28th) will churn false "stopped"/"new" series every month.

---

## 5. Schema implications (feed straight into schema design)

Consolidated from every reality above. Columns are grouped by concern.

### Transactions (mutable upsert, NOT append-only immutable)
- **Dedup keys:** `source` ENUM(plaid, ofx, qfx, csv, qif, manual, simplefin, teller), `external_id` (nullable — Plaid `transaction_id` / OFX `FITID`), `external_id_source`, `source_account_id`/`external_account_id`. **Unique constraint on `(account_id, external_id) WHERE external_id IS NOT NULL`** — scoped *per account*, never global (Firefly #10914). Plus `content_hash` and a fuzzy fingerprint (`posted_date + amount + normalized_payee + account`) for QIF/CSV rows and cross-source matching.
- **Pending lifecycle:** `pending` BOOLEAN; `pending_transaction_id` (self-FK) linking a posted row to the pending it supersedes; `superseded_by`/`resolved` status so a resolved pending doesn't render or double-count.
- **Soft-delete / mutability:** `is_removed` + `removed_at` (honor Plaid `removed` + bank deletions); apply `modified` as an in-place patch. Optional separate append-only `transaction_changelog` (field, old, new, changed_at, sync_cursor) for audit.
- **Amount & currency:** `raw_amount` (as source delivered, sign and all) **+** `signed_amount` in ONE documented internal convention (e.g. positive = inflow to account); `currency_code` (`iso_currency_code` XOR `unofficial_currency_code`); `original_currency`/`original_amount` vs `settled_amount` when a foreign charge posts in home currency.
- **Dates:** `authorized_date` (date-only, when swiped — use for spending analytics) **and** `posted_date`/`booked_date` (date-only, when money moved — use for balances/reconciliation); optional `authorized_datetime`/`posted_datetime`. Store the **user's timezone** on the user/account for correct day/month bucketing.
- **Transfers:** `transfer_group_id` (shared by both legs), `is_transfer`/`excluded_from_cashflow` BOOLEAN, `transfer_confidence` score, `transfer_source` ENUM(auto, user_confirmed, provider_category).
- **Refunds/reversals:** `related_transaction_id`/`refund_of` (link without auto-netting; refunds must *reduce category spend*, not register as income).
- **Reconciliation status:** 3-state ENUM `UNCLEARED` (blank) / `CLEARED` ('c') / `RECONCILED` ('R') — **not a boolean**; treat RECONCILED as locked.
- **Categorization:** `category_id`, `category_source` ENUM(provider, ml, rule, user) so a user correction is never overwritten; `is_reviewed`; `normalized_merchant_id` (distinct from `raw_description`); `recurring_series_id` (nullable).
- **Raw payload:** `raw_payload` JSONB to re-derive fields later.
- **Tenancy:** `owner_user_id` now (`organization_id` when orgs go live — parked per project memory).

### Categories, tags, splits
- **Categories:** hierarchical (`parent_id` self-ref or path), `income_expense` flag, optional `tax_line`/`tax_form` (arrives blank from QIF).
- **Tags:** first-class entity, many-to-many **at the split-line level**, not just per transaction.
- **Splits:** child `transaction_line` rows (category, amount, tag, memo per line) with the invariant that lines sum to the parent. A single-category-per-transaction schema *cannot* represent real Quicken data.

### Accounts & balances
- `account_type`/`account_subtype` (checking, savings, credit, loan, investment) + `is_liability` — because sign meaning and "increase = you owe more" flip for liability/investment accounts.
- `current_balance` AND `available_balance`, `balance_currency`, `balance_as_of` timestamp — provider-reported, **authoritative** (never derived from summing transactions).
- Explicit **starting/opening-balance** synthetic entry per account (= `reported_balance − Σ(known_txns)`) so a running balance reconciles; plus a "reconcile / enter current balance" adjustment path.
- `first_seen`/`linked_at` so the UI can honestly say "history starts here."
- Institution metadata (name, masked account number, connection method) for per-account re-import scoping.

### Net-worth engine
- **`account_balance_snapshot` (append-only, immutable):** `account_id`, `snapshot_date`, `balance`, `currency`, `source` ENUM(sync, manual). **One row per account per snapshot cadence — this ONE table powers the entire net-worth chart.** Populate from a **scheduled job**, not on user visit. Corrections = new rows, never in-place edits (editing a past value cascades through every chart/IRR calc).
- **Do NOT store net worth as a single mutable scalar.** Derive it: `Σ(latest snapshot per account as-of date) − liabilities`.
- On a failed sync: **carry forward last-known balance** (or mark an explicit gap); never drop the account.

### Manual assets (unified with accounts)
- `manual_asset`: `type` ENUM(real_estate, vehicle, crypto_wallet, private_equity, collectible, cash, other), `currency`, `valuation_source` ENUM(manual, zillow, price_feed, depreciation_schedule) + optional `source_ref` (Zillow URL/address), `last_valued_at`, `is_stale` + `stale_after_days`. Its snapshots flow into the *same* `account_balance_snapshot` shape with `source = manual`.

### Investments (advanced tier — mark approximate)
- `holding`: account_id, security_id, quantity, cost_basis, as_of_date (snapshot quantity+price over time if you want allocation history).
- `security`/`instrument` reference: ticker, name, asset_class, sector, expense_ratio, currency — plus `price_history` (security_id, date, close). Required for benchmark comparison, allocation checkup, fee analysis; a dataset you must source/maintain.
- `tax_lot`: holding_id, acquire_date, quantity, cost_basis_per_share, `disposal_method` ENUM(FIFO/LIFO/HIFO/LOFO/avg/specific) — only feasible with transaction ingestion; a `placeholder` transaction type for missing-history reconciling entries; an `action` field (buy/sell/reinvest/div/ESPP). Warn users lot identity is often lost in exports.
- `cash_flow_entry` (for IRR on illiquid/manual): asset_id, date, direction(in|out), amount, currency — separate from market transactions.
- Record a **performance methodology** per view (TWR from period balances vs IRR from dated cash flows); if you only snapshot balances, accept "You Index"-style backward-extrapolated approximation and label it.

### Insight / recurring / budgeting engine
- **`merchants`** (the prerequisite): raw-description alias map → `merchant_id`, `merchant_name` (clean), `logo_url`, `website`, `default_category`, `service_type` (music_streaming, video_streaming, gym…).
- **`recurring_series`:** id, user_id, account_id, merchant_id, direction, `cadence` ENUM(weekly/biweekly/semimonthly/monthly/bimonthly/quarterly/semiannual/annual), `expected_amount`, `last_amount`, `amount_is_variable`, `amount_tolerance`, `first_seen_date`, `last_charge_date`, `next_expected_date`, `occurrence_count`, `status` ENUM(early_detection/mature/inactive/cancelled), `confidence_score`, category_id. Plus a `recurring_series_transactions` join table.
- **`rules`:** id, user_id, `priority` (lower runs first), conditions structure, actions structure; enforce precedence base-category → ML → rules.
- **`category_corrections`/`ml_feedback`:** user_id, transaction_id, predicted_category, corrected_category, feature_snapshot (name, amount, day_of_week, account); gate per-user model activation at ~30 reviewed.
- **`category_budgets`:** user_id, category_id (or bucket), period, allocated_amount, rollover_enabled, rollover_balance (supports zero-based *or* flex).
- **`spending_baselines`** (materialized): user_id, category_id (+ optional merchant_id), trailing_avg over 3/6/12 mo — powers anomaly insights.
- **`insights`/`alerts`:** user_id, `type` (price_hike / duplicate_service / free_trial_converted / forgotten_annual / inactive_subscription / fee_charged / large_transaction / overspend_category / spending_anomaly / low_yield_cash), related_series_id or transaction_id, detected_amount, message, status (new/dismissed/actioned), created_at.

### Connections & security
- **`connection`/`item` (first-class, separate from Account):** `provider` ENUM(manual, csv, ofx, plaid, simplefin, teller, gocardless, enable_banking, mx, finicity, akoya), `status` ENUM(healthy/reauth_required/error/loading), `credential_ref` (encrypted — shape differs per provider: Plaid access_token / SimpleFIN Access URL / Teller mTLS cert ref), `last_successful_sync_at`, `last_error_code`, `needs_reauth`, `refresh_cadence`, `sync_cursor` (Plaid, for idempotent added/modified/removed), `days_requested` (set to max history up front — can't be cheaply extended later). An Account must be able to **migrate to a new Connection without losing transaction history** (re-linking is routine).
- **Token storage:** `encrypted_access_token` (AES-256, KMS envelope / app-layer), server-side only, **never in client payloads or logs**, access-logged, with a rotation/invalidation path (Plaid `/item/access_token/invalidate`). **No bank username/password fields anywhere.** Access tokens don't expire and are silent standing read access to someone's entire financial life — more dangerous than a password.
- **Import ledger / tombstones:** `import_run` id on each transaction (reversible batches, idempotent rollback); tombstones so user deletions **persist across re-syncs** (avoid Firefly #10090 / Actual "reimport deleted" resurrection).
- **FX:** `fx_rates` (base, quote, rate, as_of_date); convert at *display* time against dated rates, not once at ingest; decide explicitly whether historical net-worth uses rate-at-time or today's rate (they produce different history).

### Two rules to tattoo on the schema
1. **The provider's reported balance is authoritative; transactions are the itemization.** Never compute displayed balance by summing transactions.
2. **Snapshots and the changelog are append-only and sacred; the queryable transaction row is a mutable upsert.** Corrections are new rows, never in-place edits to history.

---

*Relevant file paths: none — this brief is the deliverable, returned inline.*
