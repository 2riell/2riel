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
- Investment positions/trades/FIFO or average-cost basis, valuations/dividends, performance and allocation charts. The Investments page openly states this. Investment cash accounts work; unimplemented holdings cannot be double-counted.
- Multi-currency/exchange rates. Non-PHP accounts are rejected rather than combined.
- Portable encrypted backup/validated restore, app/auto lock, clipboard safeguards and in-app complete deletion.
- Tray/native menu, OS notifications, undo (deletions use confirmation and audit).
- Fully shared generated Rust/TypeScript DTOs; the current typed frontend wrapper and runtime validators duplicate boundary definitions.
- Desktop keychain/webview end-to-end tests; real Windows/macOS compilation/install/run, signing and notarization.
- Full security/accessibility audit, larger-scale performance tests and release hardening.

## Release limits

This is a usable core milestone, not the entire requested product. Do not treat a passing browser build or independent SQLCipher test as certification of the native shell. Do not migrate sole copies of important financial records until backup/recovery and target-platform builds have been verified.

The repository rewrites the normalized projections and JSON document atomically for each save; this is suitable for small personal ledgers but does not yet have incremental writes, pagination, or audit pruning. The React app is a single view module and should be split into feature components as the remaining modules grow. Monetary display/chart coordinates use floating point after exact totals are calculated; ledger computations and storage use integer cents.
