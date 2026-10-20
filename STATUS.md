# Delivery checklist

## Implemented

- Tauri 2/Rust + React 19/TypeScript/Vite source, desktop icons, platform bundle configuration and CI configuration.
- Premium dark/light responsive layout with all requested navigation destinations, privacy toggle, keyboard search, focus-contained dialogs, success/empty/error states.
- PHP integer-minor-unit ledger with safe-integer checks, BigInt summation, Manila dates, asset/liability accounting, income/expenses/refunds/transfers/fees/signed adjustments.
- Guided first-account setup, institution presets, audited account edits, archive/restore, net-worth inclusion.
- SQLCipher encrypted file storage, cryptographically random OS-keychain-held key, no plaintext fallback, revision conflict detection, foreign keys, transactional writes, full before/after database audit.
- Working account balances, net worth/monthly cash flow, historical recorded net-worth chart and income/expense charts, month/account filters, recent activity.
- Transaction add/edit/confirmed delete, category/description search, separate transfer fees.
- Universal CSV preview/confirmation, strict dates and monetary validation, duplicate-safe imports, formula-safe transaction CSV export, template/examples.
- Verified balance snapshots and explicitly confirmed reconciliation adjustments.
- Monthly category budgets with real spending calculations and threshold notices.
- Virtual savings goals with editable fund allocations and over-allocation checks; no asset duplication.
- Separate memory-only sample data; bank sync explicitly unavailable.
- Financial-engine tests, SQLCipher repository tests and browser workflow tests.

## Not implemented / needs completion

- Full onboarding wizard, selectable currency/date/security preferences; persistent preferences.
- Account grouping/reordering, custom icons, notes/masked identifiers/interest rates and dedicated per-account history.
- Transaction splits, tags, merchants, attachments, bulk actions, recurring rules/bills/notifications, automatic categorization rules and custom category editing.
- Arbitrary date ranges, daily history, expense pie chart and complete explainable analytics.
- CSV column/date mapping, institution statement adapters, account export and duplicate override/review UX. Identical rows within one file currently cause validation to reject the preview; imports remain atomic.
- Custom-period/rollover budgets and editing existing budget limits; remove/recreate is available.
- Transfer-backed goal automation and projected completion assumptions.
- Ledger-backed investment trades, sales/FIFO, realized gains, dividends and performance/allocation charts. Informational purchase records, average cost and quoted valuations are available; they do not change ledger cash or net worth.
- Multi-currency ledger accounts and automatic exchange rates. The ledger remains PHP-only; informational USD holdings support a dated manual USD/PHP estimate.
- Portable encrypted backup/validated restore, app/auto lock, clipboard safeguards and in-app complete deletion.
- Tray/native menu, OS notifications, undo (deletions use confirmation and audit).
- Fully shared generated Rust/TypeScript DTOs; the current typed frontend wrapper and runtime validators duplicate boundary definitions.
- Desktop keychain/webview end-to-end tests; manual Windows/macOS installation/run, signing and notarization. Native Windows/macOS compilation and packaging have now passed in GitHub Actions.
- Full security/accessibility audit, larger-scale performance tests and release hardening.

## Release limits

This is a usable core milestone, not the entire requested product. Do not treat a passing browser build or independent SQLCipher test as certification of the native shell. Do not migrate sole copies of important financial records until backup/recovery and target-platform builds have been verified.

The repository rewrites the normalized projections and JSON document atomically for each save; this is suitable for small personal ledgers but does not yet have incremental writes, pagination, or audit pruning. The React app is a single view module and should be split into feature components as the remaining modules grow. Monetary display/chart coordinates use floating point after exact totals are calculated; ledger computations and storage use integer cents.

## Added in 0.2.0

- Working US ticker watchlist and informational position quantities, exact USD valuations, optional manual total cost basis, unrealized change and dated manual USD/PHP estimates. These do not post trades or affect ledger net worth.
- Finnhub quote adapter, per-ticker market timestamps, manual valuation fallback, stale-price labels and optional 60-second refresh while Investments is visible. A valid user API key and suitable provider plan are required; no authenticated live-provider test was possible without a key.
- OS-keychain API key storage, explicit opt-in, native rate limit, bounded HTTP parsing, provider errors and cache retention. No financial account data is sent to Finnhub.
- Schema 2 upgrade preserving existing records, normalized market position projection and migration tests. Provider observations do not duplicate the entire financial audit on each refresh.
- Connections for GCash, Maya, BPI, MariBank and GoTyme with official resource shortcuts and truthful unavailable sync status. BPI sign-in happens only on BPI's external official site. Bank/wallet authorization, balance read APIs and transaction sync remain unavailable; no partner access has been approved.
- Full investment trades/FIFO/sales/dividends and ledger-backed positions, streaming tick data and automatic FX are still unfinished. Existing v0.1 notes above describe the earlier milestone and are superseded by these additions.

## Added in 0.3.0

- Per-symbol purchase history with cash-based amounts or exact broker units, multiple buy prices, dates, fees, edits/removal, exact total cost and average cost per unit. Cash-derived quantities are estimates rounded down to six decimals. Realized trades/sales and ledger cash movements remain outside this feature.
- Schema 3 adds normalized purchase-lot storage, validates derived totals at frontend and native boundaries, preserves prior records and audits financial corrections. Older builds refuse this upgraded schema rather than silently discarding purchase history.

- Modernized slate/mint dark theme and matching light palette, larger typography, rounded cards, planning shortcut and responsive calculator navigation. Global ledger filters only appear where relevant.
- Seven offline calculators: loan/amortization (down payment, fees, extra payments), loan affordability, credit-card payoff, compound savings growth, target savings contribution, time-deposit net interest and emergency funds. Decimal arithmetic, cent-rounded repayment schedules and numeric CSV export; explicit assumptions, no ledger writes or remote requests. Inputs are temporary and reset when leaving the calculator page.
- Official TradingView chart shortcuts for the actual S&P 500 index and US watchlist tickers, opened externally with validated fixed-host URLs. No TradingView API key, embedded code, data scraping or access to its browser session. Its chart values do not enter SALDO totals.
- Price refresh status distinguishes sample/offline/unconfigured/manual/paused/waiting states. Opt-in 60-second polling now starts when eligible and resumes on connectivity/visibility return, with the same native cooldown. Still only while Investments is open and visible; app-wide background or streaming quotes are not implemented.
- Financial assumptions, withholding and rates are editable examples, not bank offers, tax determinations or market forecasts. Calculator results remain separate from actual balances.
