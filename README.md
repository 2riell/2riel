# SALDO

## Download the development app

- [Windows x64 setup (.exe)](https://github.com/2riell/2riel/releases/download/v0.2.0-dev.4/SALDO_0.2.0_x64-setup.exe)
- [macOS universal (.dmg), Apple silicon and Intel](https://github.com/2riell/2riel/releases/download/v0.2.0-dev.4/SALDO_0.2.0_universal.dmg)
- [Release notes and alternative MSI installer](https://github.com/2riell/2riel/releases/tag/v0.2.0-dev.4)

Version 0.3 source adds purchase amounts and multiple entry prices per symbol, average cost, seven financial calculators, a refreshed dark/light UI, TradingView chart shortcuts and clearer online refresh status. The download links above currently point to the last verified 0.2 build; the 0.3 installers are being validated. See [calculator assumptions](docs/CALCULATORS.md).

Version 0.2.0 added optional market quotes. In Investments, add SPY, VOO or IVV, configure your own Finnhub API key, then refresh or opt into 60-second refresh. See [setup and privacy notes](docs/MARKET-DATA.md). Bank/app shortcuts are available; bank login/session integration and balance sync are not.

These are unsigned development previews. Native packaging and automated checks passed on GitHub runners; installation and OS keychain workflows have not been manually tested. App lock, full investment trade accounting and portable backups are not implemented yet. Begin with sample data.

A local-first Philippine personal finance desktop app. **This is a tested development milestone, not a complete production release.** The ledger, accounts, manual transactions, monthly budgets, virtual savings earmarks, universal CSV imports, reconciliation and informational investment watchlists work. Version 0.3 adds offline planning calculators and TradingView links alongside optional Finnhub quotes and official bank/app shortcuts; see [market-data setup and limitations](docs/MARKET-DATA.md). The remaining release scope is explicit in [STATUS.md](STATUS.md).

## Run

Prerequisites: Node.js 24, npm, stable Rust with Cargo. Desktop builds additionally require the [Tauri 2 platform prerequisites](https://v2.tauri.app/start/prerequisites/).

- Windows: Visual Studio Build Tools (Desktop development with C++), WebView2, Windows SDK, and a working Perl installation for vendored OpenSSL (Strawberry Perl on PATH). WiX/MSI tools can require the VBSCRIPT optional feature.
- macOS: Xcode Command Line Tools (`xcode-select --install`), Rust for your Mac architecture, and Perl for vendored OpenSSL. The native keychain must be available.
- Linux development: a desktop session, Secret Service/keyring, C compiler, Perl, pkg-config, GLib, GTK3, WebKitGTK 4.1, libayatana-appindicator, librsvg and dbus development packages. On Ubuntu see Tauri's exact version-specific apt prerequisites.

```sh
npm ci
npm run dev          # http://localhost:1420 — session-only browser sample
npm run tauri dev    # native desktop with SQLCipher persistence + OS keychain
```

The app starts empty. Add an account with its balance **at the beginning of the opening date**, then record only movements not already included in that balance. A credit-card or loan opening debt is negative. Presets are labels, never bank connections.

The browser cannot access the OS keychain and intentionally never writes financial data to localStorage or IndexedDB. Use “Load example data” for a memory-only sample. In desktop Settings, sample mode is separate from the real database; returning reloads the desktop data.

## Check

```sh
npm test
npm run build
npm run format:check
cargo test --locked --manifest-path src-tauri/ledger-core/Cargo.toml
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo fmt --manifest-path src-tauri/ledger-core/Cargo.toml -- --check
```

Browser workflows use Playwright. Set `CHROMIUM_PATH` to your Chromium executable, or run `npx playwright install chromium` and leave `CHROMIUM_PATH` unset to use Playwright's browser.

```sh
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
```

These browser tests cover UI/accounting workflows in memory; they do **not** establish that the native OS keychain or webview works on Windows or macOS. See [VALIDATION.md](VALIDATION.md) for observed results and limits.

## Build installers on the target OS

```sh
# macOS
npm run tauri build -- --bundles app,dmg -- --locked
# Windows (PowerShell or developer command prompt)
npm run tauri build -- --bundles nsis,msi -- --locked
```

Artifacts are written to `src-tauri/target/release/bundle/`. Windows and macOS CI jobs are configured in `.github/workflows/check.yml`. The local Linux environment could not build the native shell. GitHub Actions subsequently built Windows x64 EXE/MSI and a macOS universal DMG successfully in [run 39248617740](https://github.com/2riell/2riel/actions/runs/39248617740); these are published as development preview v0.1.0-dev.2. Native installation has not been manually tested. An unsigned installer is for development, not public distribution.

For public macOS distribution, supply an Apple Developer signing identity and certificate through the CI secret store, configure `APPLE_SIGNING_IDENTITY`, and notarize with an authorized Apple ID/app-specific password/team or Apple API key using the Tauri signing documentation. On Windows, obtain an appropriate Authenticode certificate or trusted signing service, configure Tauri's Windows signing settings and timestamping, and keep private keys outside source control. Tauri updater signing is a separate concern; auto-updates are not enabled. Never commit certificates, passwords or tokens. Platform code-signing and notarization still require setup and validation.

## Use the app

- Accounts: create/edit accounts, change inclusion in net worth, archive/restore. Opening-balance edits are audited; use reconciliation adjustments to explain subsequent discrepancies.
- Transactions: income, expense, refund, transfer, signed adjustment, separate fee. Edits and confirmed deletion recalculate every affected balance. Search descriptions/categories and filter month/account. `Ctrl/Cmd+K` focuses search.
- Reconciliation: record a verified snapshot. Review its difference in Accounts; explicitly confirm an adjustment. Snapshots alone do not change money.
- CSV: choose an account, upload the universal template, review rows and confirm. Dates must be `YYYY-MM-DD`, amounts in decimal PHP with up to two fractional digits, and kind one of income/expense/refund. Transfer imports and institution-specific mappings are not supported. Repeat identical rows are detected by account/date/description/type/amount/category. Identical legitimate transactions need manual review rather than blindly retrying the file. Import never guesses whether an opening balance already includes a row; choose the opening cutoff carefully. Examples are under `examples/` (their dates may need adjustment to your account opening date).
- Budgets: category limits for the selected month. Real expenses less refunds count; transfer fees count under Bills, transfers and adjustments do not count.
- Savings: earmark funds already held in an account; allocations never increase net worth. Release allocations before spending funds that would otherwise become overallocated.
- Calculators: seven planning tools with editable example inputs, loan/card schedules and CSV export; inputs and results stay local and do not write to the ledger. See [formulas and limits](docs/CALCULATORS.md).
- Investment purchases: add a ticker, select “Purchases / add buy”, then enter each buy date, price, amount invested (USD) or exact broker units, and separate fees. Units and cost are calculated from all purchases; records can be corrected or removed. Quotes calculate unrealized value while cash ledger balances remain independent.
- TradingView: open the actual S&P 500 index or a watchlist ticker in your browser without a Finnhub key. Charts are independent of SALDO valuations. TradingView controls feed access and delay.
- Privacy/theme: header controls hide monetary text and switch light/dark mode for the session. Theme selection is not persisted yet. Exported CSV is plaintext, even with the privacy toggle on.

## Structure

```text
src/engine.ts                   Integer accounting, validation, audit events
src/engine.test.ts              Financial invariants
src/storage.ts                  Typed Tauri command wrapper; no browser persistence
src/import.ts                   Universal CSV preview and formula-safe export
src/connectors.ts               Honest connector capability/consent boundary
src/main.tsx, style.css          Responsive UI, Tailwind utilities + custom design system
src/calculators.ts              Decimal planning calculations, exact-cent loan schedules
src/Calculators.tsx             Seven offline calculators, assumptions and schedule export
src/quote-refresh.ts            Explicit refresh eligibility and cooldown logic
src-tauri/src/main.rs            OS keychain bootstrap and IPC commands
src-tauri/ledger-core/           Independently testable SQLCipher repository
src-tauri/migrations/001.sql     Schema and constraints
src-tauri/capabilities/          Minimal webview privileges
examples/                       Universal template and sample transactions
tests/                          Chromium workflow tests
```

Read [architecture/security notes](docs/ARCHITECTURE.md) before putting real financial data into this development build. Portable encrypted backup, app lock, and full recovery workflows are not implemented yet.

Market-data adapter tests: `cargo test --locked --manifest-path src-tauri/market-data/Cargo.toml`. Read `docs/MARKET-DATA.md` before enabling external quotes.
