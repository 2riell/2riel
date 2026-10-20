# Market prices, TradingView and bank access — 0.3.0

## Configure market prices

1. Install the updated desktop build and use your actual workspace (network requests are disabled in sample mode).
2. Open Investments and add a US ticker such as SPY, VOO or IVV. Leave units at zero for a watchlist. Select “Purchases / add buy” to record your purchase amounts and prices, or use manual totals for an existing position.
3. Obtain your own API key from [Finnhub](https://finnhub.io/register). Review its coverage, subscription, exchange entitlements and personal-use terms. SALDO supplies no key or subscription.
4. Enter the key in Investments, check the consent checkbox, and select “Save key & enable”. Never paste the key into chat or a public issue.
5. Select “Refresh prices”, or opt into 60-second refresh while the page is visible. The first eligible request happens immediately; reconnecting or returning to visibility resumes eligible checks after the 60-second cooldown. Navigating away from Investments, hiding it or closing the app stops scheduled checks. Internet connectivity alone does not enable this feature. The UI reports connectivity as a device hint, not proof of provider access. Tick-by-tick streaming is not implemented. Do not assume a quote is live merely because you just refreshed it: its original market timestamp and staleness are displayed. Coverage and feed delays depend on the provider plan.
6. For a PHP estimate, enter an explicit PHP-per-USD exchange rate and its date. This rate is manual, not live.

SPY, VOO and IVV are ETFs that track the S&P 500. Their share prices are not the index level. Direct S&P 500 index quotes are not a supported preset. Custom symbols use US ticker syntax (bare tickers and A/B share classes only); exchange-qualified foreign tickers are rejected so they cannot be silently labeled USD. Unsupported symbols fail visibly rather than inventing values. A maximum of ten symbols is supported.

No authenticated Finnhub call was tested in this session because no user API key was supplied. Parser, request construction and failure handling are implemented and tested without credentials. You must configure a valid key and a plan supporting your desired instruments; actual provider availability, response timing and account entitlements remain to be verified on your device.

## Financial meaning

Positions are informational, independent of the cash ledger, and excluded from SALDO net worth. Entering units does not buy/sell an asset or debit an account. USD value is units × quote price, rounded once to cents using integer arithmetic. Quantity and price precision is six decimals. PHP estimates use the dated manual rate. Unrealized change compares market value against total recorded purchase cost including fees, or optional manual cost basis if no purchase history exists. It is not realized profit, FIFO, tax accounting or broker reconciliation. Average cost per unit includes purchase fees; an extreme out-of-range average is shown as unavailable while total basis remains available.

This avoids counting both investment cash and the same shares as separate ledger assets before full investment trade accounting exists. Maintain your brokerage’s records as the authoritative source. Missing prices are explicitly unpriced and excluded from quoted totals; cost basis is never used as a fabricated market price.

Manual prices have a separately selected valuation date and “Manual valuation” provenance. Network failures, unsupported symbols, authentication failures and rate limits retain prior prices and their original timestamps. Market closures can legitimately leave an old timestamp. A fresh fetch never resets the market timestamp. A new provider quote replaces a manual price when explicitly refreshed; provider quotes do not move backward in market time relative to another provider quote.

## Privacy and implementation

Native requests go only to `https://finnhub.io/api/v1/quote`, with symbol query arguments and the documented `X-Finnhub-Token` authentication header. Redirects are refused, HTTPS is required, requests have timeouts and response sizes are capped. The OS keychain stores the API key under service `app.saldo.desktop`, item `finnhub-api-key`; it is never returned by a read command, put in the JSON database, exported, included in URLs, or printed in application errors. The key necessarily passes briefly through the native configuration command and memory while being stored/used; explicit memory zeroization is not implemented.

Tickers and the key, plus ordinary network metadata such as your IP address, go to Finnhub. Account names, units, balances, CSVs and ledger history do not. No requests occur until provider consent is explicitly saved. Refreshes are limited to once per 60 seconds at the native boundary, including failed attempts. “Disconnect & delete key” removes the key, disables refresh preferences and preserves old labeled quotes. Cached valuations remain in the encrypted local database.

Database schema 2 added `market_positions`; schema 3 adds `purchase_lots` without modifying opening balances, transactions, snapshots or audit history. Upgrades from both older schemas are tested. Existing v0.1 documents load with a disabled empty market configuration. The same app identifier, application-data directory and database key are retained. Once upgraded, older versions correctly refuse to open the newer schema; there is no downgrade or portable backup facility yet.

Provider-only quote observations update the database atomically without duplicating the full financial audit record on every refresh. Account/transaction edits, manual position and valuation edits still have before/after audit records. Informational market values cannot alter the PHP ledger. The activity list is not a historical market price series.

API documentation checked: [Finnhub quote](https://finnhub.io/docs/api/quote), [official client and header authentication](https://github.com/Finnhub-Stock-API/finnhub-go), [authentication and limits](https://www.finnhub.io/docs/api/country).

## Bank and wallet access

Connections contains external-browser shortcuts for all five requested institutions. Opening these pages never creates a SALDO bank connection, reads cookies, obtains a bank token or synchronizes balances. All five show no connection, no consent and no last synchronization. No bank-password, PIN or OTP field exists.

- **GCash:** [official login guidance](https://help.gcash.com/hc/en-us/articles/41329110227737-Are-there-other-ways-to-log-in-to-GCash) describes mobile-app sign-in.
- **Maya:** [wallet linking](https://developers.maya.ph/reference/link-a-maya-wallet) documents partner payment authorization. This does not establish a general personal balance/history API available to SALDO.
- **BPI:** [partner network](https://www.bpi.com.ph/personal/bank/digital-banking/online/partner-network) and [partner APIs](https://www.bpi.com.ph/institutional-banking/business-transactions/cashless-payment-acceptance) describe commercial integrations. SALDO has no approved partner application, authorized account-read scopes or production credentials. The shortcut opens the [official BPI Online](https://online.bpi.com.ph/) in your own browser.
- **MariBank:** [official website](https://www.maribank.ph/) describes its mobile banking application. No authorized account-read integration was verified for SALDO.
- **GoTyme:** [official app guidance](https://www.gotyme.com.ph/help/your-account/opening-a-gotyme-bank-account/downloading-the-app) is the shortcut destination. No authorized account-read integration was verified for SALDO.

Merchant/payment APIs are not a substitute for permission to read personal financial records. Real sync needs an official documented account-information access path, partner approval where required, verified scopes, a properly registered redirect/consent flow and recoverable token storage. A desktop app cannot safely hold a shared confidential OAuth client secret. No password scraping, unofficial session automation or speculative login URLs are implemented. Manual balances, statement CSV import and reconciliation continue to work for all institutions.

## TradingView chart access

Use **S&P 500 on TradingView** to open `SP:SPX`, or a ticker’s **TradingView** action for that ticker, in your external browser. A fixed TradingView HTTPS destination and validated symbol are enforced at the native boundary. Bare ticker lookup follows TradingView’s symbol resolution; check the selected exchange/instrument in its chart. No account login, API key or subscription is bundled; TradingView determines availability and delays.

These are external chart shortcuts, not embedded charts or a valuation feed. SALDO does not read chart values, cookies or your TradingView session. Viewing the actual S&P 500 index does not add an index quote to the watchlist or change ETF prices. Finnhub remains optional for automated USD position values; manual dated prices remain usable without a provider key.

TradingView’s [API policy](https://www.tradingview.com/support/solutions/43000474413-i-need-access-to-your-api-in-order-to-get-data-or-indicator-values/) explains that its REST API is for broker integrations and does not supply app market-data values. Its [widget data FAQ](https://www.tradingview.com/widget-docs/faq/data/) describes widget display and data restrictions. We do not scrape or bypass those boundaries.

## Record purchase amounts and prices

Add a ticker, select **Purchases / add buy**, and record every buy separately. Each record contains a posted date, USD price per unit, amount before fees or exact broker units, and separate USD fees. Up to 200 buys per ticker are supported. The watchlist shows total units, total invested cost including fees, average cost per unit including fees, current quoted value and unrealized gain/loss. Original purchase prices remain visible in history.

For an amount-based entry, estimated micro-units = floor(USD cents × 10^10 / price micro-dollars). No units above your entered cash amount are invented. Cash-based quantities are estimates truncated at six decimals; exact broker units should be used where available, particularly for expensive shares or tiny fractional purchases. The entered cash amount remains the recorded principal cost even when quantity precision leaves a residual; it is not a broker fill confirmation. With broker-unit entry, purchase amount is units × price rounded half up once to cents. Fees are added to cost, not units. Unit/price precision is six decimals and cash/fee precision is cents.

Total units and cost are derived from the purchase records and verified at both frontend and native boundaries. Corrections recalculate totals and are audited. Removing a purchase record is a correction, not a sale, and does not calculate realized gain. Deleting the last record clears tracked units and basis. Full sell, split, dividend, realized-profit and ledger-backed trade accounting remain unfinished.

If a ticker already has manual units/cost, starting a purchase history requires an explicit replacement checkbox. Record all prior buys before relying on that history. The original manual edit remains in the database audit. USD purchase cost is independent of any manual current USD/PHP valuation rate; historical PHP cash cost, automatic FX and non-USD securities are not implemented. Purchase amounts, prices and units stay in the encrypted local database and are never sent to Finnhub or TradingView.

Schema 3 prevents older app versions from opening the upgraded database and losing the new records on save. The app-data directory and OS database key are unchanged. Portable backup/restore remains unfinished.
