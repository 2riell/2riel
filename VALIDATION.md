# Observed validation — 19 October 2026

Environment: Debian 13 x86_64, Node 24.19.0, npm 11.9.0. Rust stable 1.99.1 was installed into a workspace-local toolchain during this session. SQLCipher was built from the pinned rusqlite/libsqlite3-sys sources with vendored OpenSSL.

| Check                                                                  | Observed result                                                                                       |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `npm test`                                                             | 13 financial-engine tests passed                                                                      |
| `cargo test --locked --manifest-path src-tauri/ledger-core/Cargo.toml` | 6 database/encryption tests passed                                                                    |
| `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`                     | 3 Chromium workflow tests passed                                                                      |
| `npm run build`                                                        | TypeScript strict build and Vite production build passed                                              |
| `npm run format:check`                                                 | Passed                                                                                                |
| Rust formatting                                                        | Both desktop and independent core formatted with rustfmt                                              |
| `npm audit --omit=dev --audit-level=high`                              | 0 known runtime dependency vulnerabilities reported                                                   |
| Full native `cargo check --manifest-path src-tauri/Cargo.toml`         | Blocked: host lacks GLib/GTK/WebKit development libraries (first failure: glib-sys pkg-config lookup) |
| Windows/macOS installers, OS keychain/native webview workflows         | Not built or tested here                                                                              |
| Remote GitHub Actions                                                  | Configured, not run                                                                                   |

The wrong-key encryption test deliberately triggers SQLCipher authentication diagnostics on stderr; the test passes by observing the failure and then reopening successfully with the correct key. No key or user financial information is printed.

Engine tests cover transfer neutrality, fees exactly once, edits/deletes and audit, snapshot immutability, repeat-import idempotency, credit-card charge/repayment accounting, earmarks, signed net worth, rejecting unsupported currencies, cent parsing, refunds, opening cutoffs/self-transfers, invalid dates/IDs and fractional cents. FX conversion and investment cost-basis tests are absent because those features are not implemented.

Database tests cover migration/persistence, conflict rejection, transaction rollback, unique import keys, allocation limits and actual on-disk encryption/correct-key reopening. These exercise the same SQLCipher repository linked by the native app, but do not exercise OS credential storage or native IPC.

Browser workflows cover initial account setup, expense entry, editing/deleting with recalculated balances, sample navigation, monetary privacy, CSV preview/repeat-import detection, theme switching, transfer with fee, snapshot observation without balance overwrite, and confirmed adjustment. Screenshots were inspected for the dark dashboard and light theme. Browser data is memory-only by design.

Build warnings: upstream Zod PURE annotation comments are ignored by Rollup; the UI bundle is approximately 773 kB / 231 kB gzip before lazy module splitting. These warnings do not fail the frontend build. They remain optimization/maintenance work.

Dependency locks (`package-lock.json`, both Cargo.lock files) are included. The runtime npm audit is a point-in-time known-vulnerability check, not a security assessment; no Rust advisory scan or comprehensive security review was performed. Native release certification remains outstanding.

## Subsequent native release validation

GitHub Actions [run 39248617740](https://github.com/2riell/2riel/actions/runs/39248617740) passed the frontend checks, six Rust SQLCipher tests on each native host, Windows x64 EXE/MSI packaging, macOS universal (Apple silicon + Intel) DMG packaging, artifact upload and release publication. Release [v0.1.0-dev.2](https://github.com/2riell/2riel/releases/tag/v0.1.0-dev.2) was built from f06dab11bfeaccb07425067d771a5b7aa4d759ea. It includes a browser regression verifying that editing a CSV transaction retains its import identity.

This supersedes the initial snapshot's statement that no native packages had been built. Signing/notarization, installation, native UI/keychain smoke tests and recovery testing remain outstanding. The binaries are unsigned development previews.

## Version 0.2 local validation

- 22 Vitest financial/market-valuation tests pass.
- 9 SQLCipher repository tests pass, including v1-to-v2 migration, informational position storage, and avoiding duplicated full audits for provider-only quote observations.
- 7 independent market-adapter tests pass, covering precise quote parsing, stale timestamps, invalid/future/missing prices, secret-safe header request construction, authentication/rate-limit/status messages and size/key constraints.
- 4 Chromium workflows pass, including manual ETF valuation, dated PHP conversion, unchanged ledger net worth, and all five bank/wallet resource shortcuts without credential forms.
- Strict TypeScript checks now include browser test/config files. Production frontend build passes.

No authenticated Finnhub quote, OS-keychain write/read or native external-browser launch was exercised locally. No banking API credentials or partner approval were available. Windows/macOS compilation, packaging and the 0.2 release must be checked in GitHub Actions separately; the earlier 0.1 build results do not validate the new native commands.
