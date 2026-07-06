# Stocks & Crypto Connectivity

**Bottom line:** No single provider covers everything a solo dev can self-serve into. Plaid is the easiest to start (free Trial, real data, includes Investments) but Fidelity through Plaid is unreliable and possibly broken. SnapTrade is the best brokerage-specialist for a solo dev (self-serve, free tier, covers Fidelity via Akoya underneath). Crypto exchanges mostly need their own read-only keys or a crypto aggregator. Build one provider-polymorphic connection layer now so you can mix Plaid + SnapTrade + direct keys + manual without new tables later.

---

## 1. Does Plaid cover it?

**What Plaid Investments gives you (and gives you well):** a clean split you should mirror in your schema.
- **Accounts** (type=investment, subtype=401k/ira/roth/brokerage/hsa/529) with balances.
- **A shared securities catalog** keyed by Plaid `security_id` (name, ticker, CUSIP/ISIN, type, close price, plus `option_contract` and `fixed_income` sub-objects).
- **Holdings** = one row per (account_id x security_id): quantity, institution price + as-of date, value, and nullable `cost_basis`.
- **Investment transactions** (up to 24 months), paginated, buy/sell/dividend/fee/transfer types.

**Access for a solo dev is genuinely good.** Sandbox is free/unlimited. Since April 15 2026 there is an **auto-approved, self-serve free Trial plan**: real Production data, up to 10 live Items, and it explicitly includes Investments + Investments Refresh and most OAuth institutions with no sales call. That is enough for a personal tool. Past 10 Items needs the full Production application (approved in a couple business days), after which Investments bills as a **recurring per-Item monthly subscription** (Holdings and Transactions are two separate subscriptions; calling the transactions endpoint silently starts both; Refresh is billed per request). Plaid never publishes the dollar figures.

**The Fidelity problem (this is the big one).** Fidelity ended screen-scraping in Oct 2023, routes aggregators through Akoya / "Fidelity Access," and publicly stated Dec 29 2025 "Fidelity does not utilize Plaid." Plaid's docs still describe a Fidelity access grant (auto ~8 weeks after Production approval, or request via support on pay-as-you-go), so some path may persist, but user-facing Fidelity links through Plaid Link are widely reported as flaky/failing. **Treat Fidelity via Plaid as high-risk / possibly unavailable, and never let a Fidelity failure block onboarding.** 401k at Fidelity NetBenefits is even less certain.

**Coverage gaps to design around:**
- **Crypto is narrow.** Plaid Investments reads only Gemini / Robinhood / SoFi-style exchanges. **Coinbase, Kraken, Binance are NOT aggregated for holdings** (Coinbase uses Plaid only for bank/ACH Auth). If crypto matters, Plaid is not your crypto solution.
- **Cost basis and lot-level tax data are the weakest part** of the model everywhere: `cost_basis`, the per-lot `lots` array, and `vested_*` exist in the schema but are nullable and inconsistently populated. Net-worth/allocation views work fine on balances+holdings+prices; anything tax-oriented needs data-present checks + manual fallback.
- **Unmapped securities** (sweep/money-market funds, proprietary mutual funds) may lack a clean ticker/CUSIP and carry `unofficial_currency_code`. Handle them.
- **Forward risk:** a live 2025-2026 fight (JPMorgan, Fidelity, Schwab charging aggregators) means big-custodian coverage and per-connection economics may degrade or shift onto you.

---

## 2. The specialists — when each beats Plaid

| Provider | Solo-dev obtainable? | When it beats Plaid |
|---|---|---|
| **SnapTrade** | **YES, fully self-serve.** Dashboard signup, credentials issued immediately, free tier (1 connected user + ~20 broker connections + trading), then pay-as-you-go. No approval gate, no minimum. | Brokerage depth. One API normalizes positions/balances/transactions/cost-basis across ~20+ US/Canada brokers, **including Fidelity (rides Akoya underneath)** and Robinhood equities via a sanctioned OAuth integration. Optional trading. This is the realistic backbone if you outgrow Plaid or need Fidelity reliably. |
| **Akoya** | **NO** (enterprise/FI-only). Sandbox is self-serve, but production needs a legal entity, data-sharing contracts, third-party risk review, SOC2/NIST posture. Explicitly "designed for commercial entities, not individual consumers." | It is the *pipe* under Fidelity and Schwab. You reach it *through* SnapTrade, never directly. Not a solo-dev option. |
| **Yodlee / MX / Finicity** | **NO** (sales-gated, no self-serve production tier). | Decent investment-data quality (esp. Yodlee/Finicity), but access is the blocker. Skip for an indie build. |

**SnapTrade pricing (transparent, indie-friendly):** free = 1 connected user. Real-time = **$2/user/mo** (first 5 free), trading included. Daily read-only = **$1/user/mo** (first 5 free), trading excluded, manual sync $0.05/op. Billed **per connected end-user, not per brokerage** (multiple brokers for one user don't double-bill). For a pure portfolio tracker, pick the $1 daily read-only tier.

**One gap SnapTrade has:** **Vanguard** is effectively absent from SnapTrade and typically needs **Plaid** (or Yodlee/Akoya) as a secondary aggregator. So Plaid and SnapTrade are complementary, not either/or.

---

## 3. Direct broker APIs

**The short list that actually exists for an individual** (great for a self-hosted single-user tool, poor for multi-tenant):

- **Interactive Brokers Client Portal Web API** — free with a funded IBKR Pro account, read + trade. Catch: needs a **per-user local Client Portal Gateway** (a small Java process running), which does not fit cloud SaaS cleanly.
- **Coinbase (via Coinbase Developer Platform)** — official read-only crypto key path. Note the **Feb 2025 change**: legacy retail keys were expired; you now mint keys through CDP with **Ed25519/JWT auth** (a pre-2025 HMAC integration will break). Read scope = `wallet:accounts:read`.
- **Charles Schwab Trader API - Individual** (successor to the retired TD Ameritrade API) — free, read + trade, self-register, but gated by a **multi-day approval + Data Accessor Agreement**. Old TDA wrappers are dead.
- **E*TRADE API** — free "individual key" tied to your own accounts only, read + trade, OAuth 1.0a, production-key approval step.
- **Robinhood Crypto Trading API** — official, but **crypto only**.

**The long list that does NOT exist for an individual:**
- **Fidelity** — no first-party retail dev API. Only via consumer-permissioned aggregation (Fidelity Access on Akoya), surfaced through **SnapTrade** or (unreliably) Plaid.
- **Vanguard** — no developer portal at all. Aggregator-only; realistically **Plaid**.
- **Robinhood equities/options** — no official API. Unofficial reverse-engineered libs (robin_stocks, etc.) are **ToS-risky (account-closure risk) — never ship them.** Use SnapTrade's sanctioned Robinhood OAuth.

**Key limitation:** all three direct brokers (IBKR/Schwab/E*TRADE) issue **single-user "individual keys"** that only serve the key owner's own accounts. Serving other people needs vendor/commercial key tiers (more approval). For anything past your own accounts, an aggregator is less friction than N direct integrations.

---

## 4. Crypto & the manual fallback — the realistic path

**Two legitimate crypto read paths, both solo-dev accessible:**
1. **Self-mint read-only exchange keys** (you're the account owner, no approval): Coinbase "View" (now via CDP/Ed25519), Kraken "Query Funds," Binance.US "Enable Reading," Gemini auditor-scoped. Read-only = balances + history, cannot trade or withdraw. Support IP-whitelisting and key rotation/revocation.
2. **A crypto aggregator** to collapse N integrations: **Vezgo** (instant free self-service keys, ~300 exchanges/wallets/chains, read-only) is the most solo-dev-friendly. For on-chain address reads, **Zerion** has the most generous no-card free tier (~60k calls/mo); Zapper / GoldRush(Covalent) / Moralis also have free tiers; a block explorer covers single-chain reads for free.

**On-chain wallets are a distinct credential shape** — a public address string with **no secret**. Do not force them through the api-key model.

**Manual entry is the universal fallback and belongs in the schema regardless.** Every reference app (Kubera, Empower, Monarch, Simplifi, Maybe) ships three crypto on-ramps: read-only API key, public wallet address, and manual entry. Manual is also the *only* way to represent real estate, vehicles, collectibles, private/illiquid holdings, **and the graceful degradation path for any Fidelity/crypto source that won't connect.**

**Model valuations as periodic, source-tagged, point-in-time snapshots** — `(asset_id, as_of_date, value, source)` where source ∈ {manual, zillow, kbb, exchange_api, onchain, plaid, snaptrade}. Net-worth-over-time is derived from the series of snapshots, not a single mutable balance. Maybe finance's immutable-Entry/Valuation → materialized-balance-cache pattern is the clean reference. Automated valuations (crypto ~8h, Zillow weekly) are just scheduled refreshes writing into the same table as a human typing a number.

---

## 5. Recommendation for THIS build

**Ship Plaid-first, behind a provider-polymorphic connection layer.** Concretely:

1. **Start on Plaid's free Trial (10 Items).** It's the fastest path to real data, includes Investments, and is the one realistic self-serve route to **Vanguard**. Attempt Fidelity through it, but **assume it may not work** and wire the manual/CSV fallback for Fidelity from day one. Design onboarding around OAuth redirects and the 1-2 minute initial-sync delay, with a per-institution "supported?" capability check.

2. **Build the abstraction so SnapTrade, Akoya-via-SnapTrade, direct keys, and manual all drop in with zero new tables.** The whole point: a solo dev can only *get approved for* Plaid (self-serve), SnapTrade (self-serve), direct broker keys for *your own* accounts (gated but obtainable), Coinbase/exchange read-only keys (instant), and manual (no third party). Everything else (Akoya direct, Yodlee, MX, Finicity) is enterprise-gated and off the table. The layer must route Fidelity → SnapTrade when Plaid fails, Vanguard → Plaid, crypto → exchange key/aggregator, and anything unsupported → manual.

3. **The schema this requires (confirmed):**

   - **`connections`** with a **type discriminator** so the read paths coexist: `provider` (plaid | snaptrade | coinbase | ibkr | schwab | etrade | vezgo | manual) and `connection_type` (oauth_access_token | api_key_secret | onchain_address | aggregator_token | manual). A **generic per-connection credential store, encrypted at rest** (reuse the codebase's AES-GCM rotation), holding whichever of {access_token} OR {api_key + secret + optional passphrase} OR {address string} applies — plus metadata: label, granted scopes (enforce/record read-only intent), last_synced_at, status, sync watermark, `cost_basis_available` flag.
   - **A per-connection capability matrix** rather than assuming uniformity: `{read_positions, read_balances, read_transactions, read_cost_basis, trade_equities, trade_options, trade_crypto}`. Persist granted scope; enforce least privilege (store read-only vs trade-enabled tokens separately); keep any trading surface optional and gated behind explicit consent.
   - **`accounts` + shared `securities` catalog + `holdings` (account x security) + `transactions`** — mirror Plaid's split, since SnapTrade normalizes to the same shape. Store `security_id` but reconcile on CUSIP/ISIN/ticker and expect it to change on corporate actions. Canonicalize the transaction taxonomy on ingest (every provider names buys/sells/dividends/transfers differently).
   - **`manual_accounts` / other-assets** — universal fallback for Fidelity-that-won't-connect, real estate, vehicles, collectibles, private holdings.
   - **`valuations`** — periodic, source-tagged, point-in-time `(asset_id, as_of_date, value, source)`; net-worth history derived from the series; one write path shared by manual, exchange, on-chain, and automated sources.

4. **Treat everything tax-related as optional/nullable** (cost_basis, lots, vested, realized gain/loss). Make the net-worth/allocation view work on balances+holdings+prices alone; gate tax features behind data-present checks.

5. **Cost discipline:** Plaid bills per-Item per-month per-subscription (transactions doubles it via the implicit Holdings sub) — cache deliberately, use Refresh sparingly, delete stale Items to stop the meter. SnapTrade bills per active user (pick $1 daily read-only for a tracker). Direct/exchange keys are free.

**Honest summary of what you can actually get today, no sales calls:** Plaid Trial (10 live Items, includes Investments, real data), SnapTrade free tier then $1-2/user/mo, Coinbase/Kraken/Binance/Gemini read-only keys (instant), Vezgo/Zerion free crypto aggregation, and IBKR/Schwab/E*TRADE keys for your *own* accounts (obtainable but with approval latency). What you cannot get: Akoya/Yodlee/MX/Finicity production, a Fidelity or Vanguard first-party retail API, or an official Robinhood equities API. Plan around those four "no"s and the Fidelity-via-Plaid coin-flip, and the build is very achievable solo.
