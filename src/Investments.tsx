import { useEffect, useRef, useState, type FormEvent } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  RefreshCw,
  Plus,
  Trash2,
  KeyRound,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { desktop } from "./storage";
import {
  quoteSchema,
  marketSchema,
  scaled,
  unscale,
  positionValue,
  marketTotals,
  toPhp,
  quoteAge,
  type Market,
  type Quote,
  type Position,
} from "./market";
import { minor, today, id } from "./engine";
import { z } from "zod";
const batchSchema = z.object({
  quotes: z.array(quoteSchema),
  errors: z.array(z.object({ symbol: z.string(), message: z.string() })),
});
type Props = {
  market: Market;
  sample: boolean;
  hidden: boolean;
  persist: (market: Market, action: string) => Promise<boolean>;
};
const fmt = (minor: number, currency = "USD") =>
  new Intl.NumberFormat("en-PH", { style: "currency", currency }).format(
    minor / 100,
  );
export async function openResource(resource: string, url: string) {
  if (desktop) await invoke("open_official_resource", { resource });
  else window.open(url, "_blank", "noopener,noreferrer");
}
export default function Investments({
  market,
  sample,
  hidden,
  persist,
}: Props) {
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [working, setWorking] = useState(false),
    [hasKey, setHasKey] = useState(false),
    [apiKey, setApiKey] = useState(""),
    [consent, setConsent] = useState(false),
    [showForm, setShowForm] = useState(false),
    [editing, setEditing] = useState<Position | null>(null);
  const latest = useRef(market),
    inflight = useRef(false),
    active = useRef(true);
  latest.current = market;
  useEffect(() => {
    active.current = true;
    if (desktop && !sample)
      invoke<boolean>("market_key_status")
        .then(setHasKey)
        .catch(() =>
          setError(
            "OS credential store unavailable. Manual valuations remain available.",
          ),
        );
    return () => {
      active.current = false;
    };
  }, [sample]);
  const display = (n: number, currency = "USD") =>
    hidden ? `${currency} ••••••` : fmt(n, currency);
  async function update(m: Market, action: string) {
    const next = marketSchema.parse(m);
    const saved = await persist(next, action);
    if (saved) {
      latest.current = next;
      setMessage(action + " saved");
    }
    return saved;
  }
  async function refresh() {
    if (inflight.current || !desktop || sample) return;
    inflight.current = true;
    setWorking(true);
    setError("");
    try {
      const data = batchSchema.parse(await invoke("refresh_market_quotes"));
      if (!active.current) return;
      const m = structuredClone(latest.current);
      for (const p of m.positions) {
        const q = data.quotes.find((q) => q.symbol === p.symbol);
        if (
          q &&
          (!p.quote ||
            p.quote.provider === "manual" ||
            q.timestamp >= p.quote.timestamp)
        )
          p.quote = q;
      }
      if (data.quotes.length) await update(m, "Market prices updated");
      if (data.errors.length)
        setError(data.errors.map((e) => `${e.symbol}: ${e.message}`).join(" "));
    } catch (e) {
      if (active.current) setError(String(e));
    } finally {
      inflight.current = false;
      if (active.current) setWorking(false);
    }
  }
  useEffect(() => {
    if (!market.enabled || !market.autoRefresh || sample || !desktop) return;
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 60_000);
    return () => clearInterval(timer);
  }, [market.enabled, market.autoRefresh, sample]);
  async function configure(e: FormEvent) {
    e.preventDefault();
    setWorking(true);
    setError("");
    try {
      await invoke("set_market_key", { apiKey, consent });
      setApiKey("");
      setHasKey(true);
      await update(
        { ...latest.current, enabled: true },
        "Market provider enabled",
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setWorking(false);
    }
  }
  async function disconnect() {
    setWorking(true);
    setError("");
    try {
      await invoke("clear_market_key");
      setHasKey(false);
      await update(
        { ...latest.current, enabled: false, autoRefresh: false },
        "Market provider disconnected",
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setWorking(false);
    }
  }
  function savePosition(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    try {
      const f = new FormData(e.currentTarget),
        get = (k: string) => String(f.get(k) || "").trim();
      const p: Position = {
        id: editing?.id || id(),
        symbol: get("symbol").toUpperCase(),
        name: get("name"),
        unitsMicros: scaled(get("units")),
        costBasisUsdMinor: get("cost") ? minor(get("cost")) : null,
        quote: editing?.quote ?? null,
      };
      if (editing?.symbol !== p.symbol) p.quote = null;
      const m = {
        ...latest.current,
        positions: editing
          ? latest.current.positions.map((x) => (x.id === p.id ? p : x))
          : [...latest.current.positions, p],
      };
      void update(m, editing ? "Position updated" : "Ticker added")
        .then((ok) => {
          if (ok) {
            setShowForm(false);
            setEditing(null);
          }
        })
        .catch((e) => setError(String(e)));
    } catch (e) {
      setError(String(e));
    }
  }
  function manual(p: Position) {
    const price = prompt(
      `Manual USD unit price for ${p.symbol} (up to 6 decimals)`,
    );
    if (price === null) return;
    const date = prompt("Valuation date (YYYY-MM-DD)", today());
    if (date === null) return;
    try {
      if (
        !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
        new Date(date).toISOString().slice(0, 10) !== date ||
        date > today()
      )
        throw Error("Use a valid posted valuation date");
      const q: Quote = {
        symbol: p.symbol,
        priceMicros: scaled(price),
        previousCloseMicros: null,
        timestamp: Math.floor(Date.parse(`${date}T00:00:00+08:00`) / 1000),
        receivedAt: new Date().toISOString(),
        provider: "manual",
      };
      void update(
        {
          ...latest.current,
          positions: latest.current.positions.map((x) =>
            x.id === p.id ? { ...x, quote: q } : x,
          ),
        },
        "Manual valuation",
      ).catch((e) => setError(String(e)));
    } catch (e) {
      setError(String(e));
    }
  }
  const totals = marketTotals(market);
  return (
    <div className="investment-module">
      <section className="panel investment-intro">
        <div>
          <span className="eyebrow">MARKET WATCH & VALUATION</span>
          <h2>A clearer view of your investments.</h2>
          <p>
            Track US shares and ETFs, including S&P 500 ETFs SPY, VOO and IVV.
            ETF prices are not the S&P 500 index level.
          </p>
          <p>
            Informational positions are excluded from SALDO net worth. They do
            not buy/sell assets or move investment cash. Trade accounting and
            realized gains are not implemented.
          </p>
        </div>
        <button
          className="primary"
          onClick={() => {
            setEditing(null);
            setShowForm(!showForm);
          }}
          disabled={market.positions.length >= 10}
        >
          <Plus size={16} /> Add ticker
        </button>
      </section>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="notice" role="status">
          {message}
          <button className="text" onClick={() => setMessage("")}>
            Dismiss
          </button>
        </div>
      )}
      <div className="stats">
        <section className="stat">
          <div className="stat-label">Quoted position value</div>
          <div className="stat-value">{display(totals.usd)}</div>
          <small>
            {totals.unpriced} position(s) have units without a price; omitted
            from this total.
          </small>
        </section>
        <section className="stat">
          <div className="stat-label">PHP estimate</div>
          <div className="stat-value">
            {totals.php === null
              ? "Set an FX rate"
              : display(totals.php, "PHP")}
          </div>
          <small>
            {market.fx
              ? `Manual USD/PHP rate ${hidden ? "hidden" : unscale(market.fx.rateMicros)} · ${market.fx.date}`
              : "USD and PHP are never silently combined."}
          </small>
        </section>
        <section className="stat">
          <div className="stat-label">Quote source</div>
          <div className="stat-value">
            {market.enabled ? "Finnhub" : "Manual / offline"}
          </div>
          <small>
            Feed delay and ticker coverage depend on your provider plan. Auto
            refresh is polling, not a streaming feed.
          </small>
        </section>
      </div>
      {showForm && (
        <section className="panel investment-form">
          <h2>{editing ? "Edit informational position" : "Add a US ticker"}</h2>
          <form onSubmit={savePosition}>
            <label>
              US ticker
              <input
                required
                name="symbol"
                defaultValue={editing?.symbol || ""}
                placeholder="SPY, VOO, IVV, AAPL"
                pattern="[A-Za-z][A-Za-z0-9]{0,9}(?:[.\-][ABab])?"
              />
            </label>
            <label>
              Display name
              <input
                required
                name="name"
                defaultValue={editing?.name || ""}
                placeholder="S&P 500 ETF"
                maxLength={100}
              />
            </label>
            <label>
              Units (0 for watchlist only)
              <input
                required
                name="units"
                defaultValue={editing ? unscale(editing.unitsMicros) : "0"}
              />
            </label>
            <label>
              Optional total cost basis (USD)
              <input
                name="cost"
                defaultValue={
                  editing?.costBasisUsdMinor !== null &&
                  editing?.costBasisUsdMinor !== undefined
                    ? (editing.costBasisUsdMinor / 100).toFixed(2)
                    : ""
                }
              />
            </label>
            <div className="row-actions">
              <button className="primary" type="submit">
                Save ticker
              </button>
              <button type="button" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Your watchlist & positions</h2>
            <p>
              Last price time is the provider’s market timestamp, not the time
              you clicked refresh.
            </p>
          </div>
          <button
            onClick={() => void refresh()}
            disabled={
              working ||
              sample ||
              !desktop ||
              !market.enabled ||
              !hasKey ||
              !market.positions.length
            }
          >
            <RefreshCw size={15} />
            {working ? "Refreshing…" : "Refresh prices"}
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticker / source time</th>
                <th>Units</th>
                <th className="right">USD unit price</th>
                <th className="right">Value / unrealized gain</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {market.positions.map((p) => {
                const value = positionValue(p);
                const gain =
                  value === null || p.costBasisUsdMinor === null
                    ? null
                    : value - p.costBasisUsdMinor;
                return (
                  <tr key={p.id}>
                    <td>
                      <strong>
                        {p.symbol} · {p.name}
                      </strong>
                      <small>
                        {p.quote ? quoteAge(p.quote) : "No quote available"}
                      </small>
                      {p.quote && (
                        <small>
                          {new Date(p.quote.timestamp * 1000).toLocaleString(
                            "en-PH",
                            { timeZone: "Asia/Manila" },
                          )}{" "}
                          · Manila
                        </small>
                      )}
                    </td>
                    <td>{hidden ? "•••" : unscale(p.unitsMicros)}</td>
                    <td className="right mono">
                      {p.quote
                        ? hidden
                          ? "USD •••"
                          : new Intl.NumberFormat("en-US", {
                              style: "currency",
                              currency: "USD",
                              maximumFractionDigits: 6,
                            }).format(p.quote.priceMicros / 1_000_000)
                        : "—"}
                    </td>
                    <td className="right mono">
                      {value === null ? "Unpriced" : display(value)}
                      {gain !== null && (
                        <small className={gain >= 0 ? "positive" : "danger"}>
                          {display(gain)} unrealized · manual cost basis
                        </small>
                      )}
                      {value !== null && market.fx && (
                        <small>
                          {display(toPhp(value, market.fx)!, "PHP")} estimate
                        </small>
                      )}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="text"
                          onClick={() => {
                            setEditing(p);
                            setShowForm(true);
                          }}
                        >
                          Edit
                        </button>
                        <button className="text" onClick={() => manual(p)}>
                          Manual price
                        </button>
                        <button
                          className="icon danger"
                          aria-label={`Remove ${p.symbol}`}
                          onClick={() => {
                            if (
                              confirm(
                                `Remove ${p.symbol} from the watchlist? No cash or ledger entries will change.`,
                              )
                            )
                              void update(
                                {
                                  ...latest.current,
                                  positions: latest.current.positions.filter(
                                    (x) => x.id !== p.id,
                                  ),
                                },
                                "Ticker removed",
                              ).catch((e) => setError(String(e)));
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!market.positions.length && (
            <div className="empty">
              Add SPY, VOO or IVV to track an S&P 500 ETF. Prices start empty
              and are never simulated.
            </div>
          )}
        </div>
      </section>
      <div className="dashboard-grid">
        <section className="panel investment-form">
          <h2>Market-data connection</h2>
          <p>
            <ShieldCheck size={13} /> Only ticker symbols and your Finnhub key
            are sent to Finnhub. Your quantities, balances, account names and
            financial history stay on this device.
          </p>
          <p>
            The key is stored in your OS keychain and never returned to this
            screen. A Finnhub account, coverage and applicable subscription
            terms are required. No key is included.
          </p>
          <button
            className="text"
            onClick={() =>
              void openResource("finnhub", "https://finnhub.io/register").catch(
                (e) => setError(String(e)),
              )
            }
          >
            <ExternalLink size={13} /> Get your own Finnhub API key
          </button>
          <form onSubmit={configure}>
            <label>
              Finnhub API key
              <input
                autoComplete="off"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
                placeholder={
                  hasKey
                    ? "Key saved in OS keychain; enter to replace"
                    : "Paste your key here, never in chat"
                }
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />{" "}
              I consent to sending these tickers to Finnhub and understand plan
              limits and possible quote delays.
            </label>
            <div className="row-actions">
              <button
                className="primary"
                disabled={working || sample || !desktop || !consent}
              >
                <KeyRound size={14} /> Save key & enable
              </button>
              {hasKey && (
                <button
                  type="button"
                  disabled={working}
                  onClick={() => void disconnect()}
                >
                  Disconnect & delete key
                </button>
              )}
            </div>
          </form>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={market.autoRefresh}
              disabled={
                !market.enabled || !hasKey || sample || !desktop || working
              }
              onChange={(e) =>
                void update(
                  { ...latest.current, autoRefresh: e.target.checked },
                  "Auto refresh preference",
                ).catch((e) => setError(String(e)))
              }
            />{" "}
            Refresh every 60 seconds while this page is visible
          </label>
          {(sample || !desktop) && (
            <p>
              Network quotes and credentials are disabled in sample mode. Use
              the desktop real workspace to connect. Manual prices work here.
            </p>
          )}
        </section>
        <section className="panel investment-form">
          <h2>Dated USD → PHP estimate</h2>
          <p>
            Enter an explicit PHP-per-USD exchange rate. This rate is manual,
            not live, and does not change the PHP ledger.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              try {
                void update(
                  {
                    ...latest.current,
                    fx: {
                      rateMicros: scaled(String(f.get("rate"))),
                      date: String(f.get("date")),
                    },
                  },
                  "Exchange rate updated",
                ).catch((e) => setError(String(e)));
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            <label>
              PHP per 1 USD
              <input
                required
                name="rate"
                defaultValue={market.fx ? unscale(market.fx.rateMicros) : ""}
                placeholder="Enter your dated rate"
              />
            </label>
            <label>
              Rate date
              <input
                required
                name="date"
                type="date"
                defaultValue={market.fx?.date || today()}
                max={today()}
              />
            </label>
            <button>Save exchange rate</button>
          </form>
          {market.fx && (
            <button
              className="text"
              onClick={() =>
                void update(
                  { ...latest.current, fx: null },
                  "Exchange rate removed",
                ).catch((e) => setError(String(e)))
              }
            >
              Remove conversion
            </button>
          )}
        </section>
      </div>
    </div>
  );
}
