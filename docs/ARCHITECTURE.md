# Architecture and security

## Trust and persistence

The native app opens `<OS app-data>/app.saldo.desktop/saldo.db` (Tauri resolves the platform path). The keyring service `app.saldo.desktop`, item `database-key`, contains a randomly generated 256-bit key as hex. macOS uses its native Keychain; Windows uses its native Credential Manager; Linux requires Secret Service. The operating system account is the security boundary. A compromised logged-in desktop or webview can access decrypted data; encryption at rest does not prevent that.

SQLCipher is compiled through rusqlite's `bundled-sqlcipher-vendored-openssl` feature. Startup requires a cipher version, validates key shape, and refuses plaintext fallback. It refuses to create a replacement key for an existing database. SQLCipher page authentication rejects incorrect keys. The disk test checks the non-SQLite file header, incorrect-key failure and successful correct-key reopening.

No custom cryptographic algorithm, bank login, mandatory cloud, telemetry or financial-data network service is used. Production CSP restricts scripts and connectivity; no shell, arbitrary file, HTTP or filesystem plugin is exposed to the renderer. IPC consists of load_state and save_state. The file chooser accepts explicit user-selected CSV; imports are limited to 2 MB and saves to 10 MB. CSV cells are inert text; exports escape spreadsheet formulas. Financial data is not logged intentionally; error messages are local.

The random key lives in process memory while opening the database; explicit zeroization and locked memory are not implemented. SQLCipher memory and OS swap behavior are not audited. The privacy button hides formatted monetary text; it is not an application lock and does not redact exports or original data. Chart shapes can still reveal relative trends. No portable backup exists yet. Theme and filters are session-only.

**Recovery:** a database file alone is insufficient without its OS keychain key. Losing/resetting the OS credential store can make all local data unrecoverable. OS keychain migration/backup behavior differs by platform and has not been tested here. Do not rotate/remove keys or reinstall the OS before arranging a verified recovery path. An app password cannot recover the data because app passwords are not implemented. Manually copy neither keys nor plaintext records into source control.

**Deletion:** no in-app deletion workflow exists yet. For development data, quit the app, remove its resolved application-data directory and remove the matching keychain item using the OS credential manager. Ensure you are targeting SALDO's service/item, not another application's credentials. Secure physical erasure on SSDs, OS backups and snapshots cannot be guaranteed by file deletion.

## Ledger invariants

- PHP minor units are signed integers. Parsing uses decimal strings and BigInt, never float multiplication for ledger input. Totals use BigInt, then checked conversion for frontend safe integers. Rust reads integers and checks bounds, using i128 for aggregate validation. Database fields are INTEGER.
- Asset balances are positive; liability debt balances are negative. A credit-card purchase is an expense movement that makes its balance more negative. Repayment is a cash-to-card transfer. Credit balances can become positive after repayment/refund.
- Account balance = opening + posted movements. Income/refund/adjustment add signed amounts. Expense subtracts amount. Transfer subtracts at source and adds at destination. Fee subtracts only at source and counts under Bills. Transfers and adjustments do not enter income/expense reports.
- One transfer row encodes both account effects. The system is an account-movement ledger, not a full general-ledger double-entry accounting package. No shadow cash asset is created for virtual goals.
- Opening is the balance at the beginning of the given date. Earlier imports are refused. The user must exclude movements already contained in that opening; an importer cannot establish this from universal CSV alone.
- All entered transaction dates are posted dates, not future schedules. Dates are calendar-validated, Manila's date controls defaults/future checks. Historical account opening and entry dates limit chart balances. No synthetic historical growth is generated.
- Snapshots are observations only. Confirmed adjustments are separate signed ledger entries with their own provenance. Repeated clicks after adjustment recalculate discrepancy as zero.
- Virtual goal allocations must not exceed the nonnegative calculated account balance. They reserve assets, never increase assets. Funding trades and actual investment positions are deferred to avoid incomplete cost-basis logic.
- All currencies are PHP. Unsupported currency is rejected; there is no guessed FX conversion.

## Database schema and writes

Migration 001 creates:

| Table     | Purpose                                                                               |
| --------- | ------------------------------------------------------------------------------------- |
| accounts  | Institution, nickname, type, PHP, opening/date, inclusion/archive                     |
| entries   | Dated account movement; optional transfer destination; fee/category/source/import key |
| budgets   | Category/month limit                                                                  |
| goals     | Account-backed virtual allocation, target and due date                                |
| snapshots | Verified account observations                                                         |
| app_state | Renderer document plus monotonic revision                                             |
| audit     | Immutable-in-normal-operation full previous/new documents per save                    |

Foreign keys, primary keys, unique import keys, positive non-adjustment amounts, fee bounds and transfer constraints protect writes. IPC validates JSON fields and dates; additional SQL and wider integer checks enforce opening cutoffs, account existence, monetary precision and goal allocation. The frontend runs its own strict Zod validation before saving and after loading. Renderer types are compile-time TypeScript types, not generated Rust bindings yet.

A save begins a SQLite transaction, checks expected revision, replaces dependent projections in foreign-key-safe order, validates them, appends audit, and updates the JSON document/revision. Any failure rolls the entire transaction back. The audit table holds full old/new records, including entries the user later deletes; there is no automatic history purge. JSON and normalized tables are one atomic persistence unit. Each entry has one transfer pair rather than a separate transaction-lines table; merchants, investments, currencies/rates, recurring rules and settings tables belong to future migrations.

Current schema version 1 is applied transactionally only to version 0; a newer database is rejected. There is no down-migration or restore pathway. DELETE journaling avoids relying on an unhandled WAL-copy backup. SQLCipher encrypts database pages; plaintext CSV exports remain the user's responsibility.

## Imports and connectors

The universal adapter parses Papa Parse CSV, maps fixed headers, validates decimal strings and YYYY-MM-DD dates, classifies only income/expense/refund, then presents an explicit preview. Natural duplicate identity is account/date/description/type/cents/category. This provides idempotency but cannot distinguish truly identical separate purchases. Do not describe it as bank transaction-ID deduplication. Each stored key is unique; database constraints prevent race duplicates. UI preview rejects duplicate keys within the same file, while retries of an already committed file show no new rows.

`AccountConnector` models actual capabilities, consent, error and last success. Manual/CSV is ready; bank sync has no capabilities and is unavailable. No institution APIs have been verified or implemented. Adding a connector requires documented official authorized access, explicit consent, scoped credentials, error handling and independently verified data provenance. Never scrape bank passwords, OTPs or sessions.

## Next release gates

Implement portable encrypted backup and restore with recovery tests; application lock; feature-level UI extraction; generated command DTOs; native integration tests on both operating systems; signed/notarized installers; OS keychain recovery/deletion and lock behavior tests; screen-reader/contrast review; investment cash/position invariants before enabling portfolios. Dependencies are locked, but their compatibility and security still require ongoing maintenance and audit before a public release.

## Version 0.2 additions

See [market data and bank access](MARKET-DATA.md). Schema 2 adds informational position projections; existing state defaults to disabled market requests. Native market commands use a fixed HTTPS provider endpoint and OS-keychain secrets. The old description of IPC limited to load/save applies to v0.1; v0.2 also exposes consent-gated key configuration/quotes and a fixed allowlist of official external resources. It exposes no arbitrary URL opener, bank credentials, session scraper or account sync. Provider-only quote updates are non-ledger observations and do not duplicate the entire financial audit. All actual financial edits continue to audit.
