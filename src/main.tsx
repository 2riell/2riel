import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard,
  Wallet,
  ArrowLeftRight,
  ChartNoAxesCombined,
  Target,
  PiggyBank,
  Settings,
  Plus,
  ArrowUpRight,
  ArrowDownLeft,
  Eye,
  EyeOff,
  Search,
  ShieldCheck,
  ChevronRight,
  Sun,
  Moon,
  X,
  Upload,
  Download,
  TrendingUp,
  Link2,
  Calculator,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import {
  balance,
  cashFlow,
  categories,
  commit,
  demo,
  empty,
  id,
  importEntries,
  minor,
  netWorth,
  presets,
  spent,
  sum,
  today,
  validate,
  type State,
  type Entry,
  type Account,
} from "./engine";
import { desktop, load, save } from "./storage";
import { previewCSV, csvExport } from "./import";
import Investments from "./Investments";
import Connections from "./Connections";
import Calculators from "./Calculators";
import type { Market } from "./market";
import "./style.css";
const nav = [
  ["Overview", LayoutDashboard],
  ["Accounts", Wallet],
  ["Transactions", ArrowLeftRight],
  ["Budgets", PiggyBank],
  ["Savings", Target],
  ["Investments", TrendingUp],
  ["Analytics", ChartNoAxesCombined],
  ["Calculators", Calculator],
  ["Connections", Link2],
  ["Settings", Settings],
] as const;
function App() {
  const [s, setS] = useState<State>(empty),
    [ready, setReady] = useState(false),
    [page, setPage] = useState("Overview"),
    [modal, setModal] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [hidden, setHidden] = useState(false),
    [light, setLight] = useState(false),
    [sample, setSample] = useState(!desktop),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [month, setMonth] = useState(today().slice(0, 7)),
    [preview, setPreview] = useState<Entry[]>([]),
    [edit, setEdit] = useState<Entry | undefined>(),
    [editAccount, setEditAccount] = useState<Account | undefined>(),
    [selected, setSelected] = useState("all");
  const currentState = useRef(s),
    writeLock = useRef(false);
  currentState.current = s;
  async function persistMarket(
    market: Market,
    action: string,
  ): Promise<boolean> {
    if (writeLock.current) return false;
    writeLock.current = true;
    setBusy(true);
    try {
      const n =
        action === "Market prices updated"
          ? validate({
              ...structuredClone(currentState.current),
              market,
              revision: currentState.current.revision + 1,
            })
          : commit(currentState.current, action, (d) => {
              d.market = market;
            });
      if (!sample) await save(n);
      currentState.current = n;
      setS(n);
      return true;
    } catch (e) {
      setError(String(e));
      return false;
    } finally {
      writeLock.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    load()
      .then((x) => {
        setS(x);
        setReady(true);
      })
      .catch((e) => {
        setError(String(e));
        setReady(true);
      });
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = light ? "light" : "dark";
  }, [light]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        document.getElementById("search")?.focus();
      }
      if (e.key === "Escape") setModal("");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  const money = (n: number) =>
    hidden
      ? "₱ ••••••"
      : new Intl.NumberFormat("en-PH", {
          style: "currency",
          currency: "PHP",
          minimumFractionDigits: 2,
        }).format(n / 100);
  async function apply(action: string, fn: (d: State) => void) {
    if (writeLock.current) return;
    writeLock.current = true;
    setBusy(true);
    setError("");
    try {
      const n = commit(currentState.current, action, fn);
      if (!sample) await save(n);
      currentState.current = n;
      setS(n);
      setNotice(`${action} saved`);
      setModal("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      writeLock.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement;
    const dialog = document.querySelector("[role=dialog]")!;
    const focusables = () =>
      Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input,select,[tabindex="0"]',
        ),
      );
    focusables()[0]?.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const f = focusables(),
        first = f[0],
        last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [modal]);
  const filtered: State = {
    ...s,
    accounts: s.accounts.filter((a) => selected === "all" || a.id === selected),
    entries: s.entries.filter(
      (e) => selected === "all" || e.account === selected || e.to === selected,
    ),
  };
  const flow = cashFlow(filtered, `${month}-01`, `${month}-31`);
  const worth = netWorth(filtered);
  const active = s.accounts.filter((a) => !a.archived);
  const es = filtered.entries
    .filter(
      (e) =>
        e.date.startsWith(month) &&
        `${e.description} ${e.category}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    )
    .sort((a, b) => b.date.localeCompare(a.date));
  const trend = Array.from({ length: 12 }, (_, i) => {
    const date = new Date(`${month}-01T00:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() - 11 + i);
    const m = date.toISOString().slice(0, 7),
      end = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0))
        .toISOString()
        .slice(0, 10);
    return {
      month: date.toLocaleDateString("en", { month: "short", timeZone: "UTC" }),
      worth:
        netWorth(
          {
            ...filtered,
            accounts: filtered.accounts.filter((a) => a.opened <= end),
          },
          end,
        ) / 100,
      ...Object.fromEntries(
        Object.entries(cashFlow(filtered, `${m}-01`, end)).map(([k, v]) => [
          k,
          v / 100,
        ]),
      ),
    };
  });
  function open(m: string) {
    if (m === "Account") setEditAccount(undefined);
    setError("");
    setModal(m);
  }
  function exportCSV() {
    const url = URL.createObjectURL(
      new Blob([csvExport(s)], { type: "text/csv" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "saldo-transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const str = (k: string) => String(f.get(k) || "");
    try {
      if (modal === "Account")
        void apply("Account", (n) => {
          const account: Account = {
            id: editAccount?.id || id(),
            name: str("name"),
            institution: str("institution"),
            type: str("type") as State["accounts"][number]["type"],
            opening: minor(str("opening")),
            opened: str("date"),
            currency: "PHP",
            include: editAccount?.include ?? true,
            archived: editAccount?.archived ?? false,
          };
          n.accounts = editAccount
            ? n.accounts.map((a) => (a.id === editAccount.id ? account : a))
            : [...n.accounts, account];
          n.onboarded = true;
        });
      if (modal === "Transaction")
        void apply(edit ? "Transaction updated" : "Transaction", (n) => {
          const entry: Entry = {
            id: edit?.id || id(),
            description: str("description"),
            date: str("date"),
            kind: str("kind") as Entry["kind"],
            account: str("account"),
            ...(str("kind") === "transfer" ? { to: str("to") } : {}),
            amount: minor(str("amount")),
            fee: minor(str("fee") || "0"),
            category: str("category"),
            source: edit?.source ?? "manual",
            ...(edit?.importKey ? { importKey: edit.importKey } : {}),
          };
          n.entries = edit
            ? n.entries.map((x) => (x.id === edit.id ? entry : x))
            : [...n.entries, entry];
        });
      if (modal === "Budget")
        void apply("Budget", (n) => {
          n.budgets.push({
            id: id(),
            category: str("category"),
            limit: minor(str("amount")),
            month,
          });
        });
      if (modal === "Goal")
        void apply("Savings goal", (n) => {
          n.goals.push({
            id: id(),
            name: str("name"),
            target: minor(str("amount")),
            allocated: minor(str("allocated")),
            account: str("account"),
            due: str("date"),
          });
        });
      if (modal === "Reconcile") {
        const a = s.accounts.find((a) => a.id === str("account"))!;
        const actual = minor(str("amount"));
        void apply("Balance snapshot", (n) => {
          n.snapshots.push({ id: id(), account: a.id, date: today(), actual });
        });
        setNotice(
          `Snapshot recorded. Difference: ${money(actual - balance(s, a))}. Review in Accounts.`,
        );
      }
    } catch (e) {
      setError(String(e));
    }
  }
  const field = (
    label: string,
    name: string,
    type = "text",
    value?: string,
  ) => (
    <label>
      {label}
      <input
        required
        name={name}
        type={type}
        defaultValue={value}
        step={type === "number" ? "0.01" : undefined}
      />
    </label>
  );
  const accountsSelect = (
    <label>
      Account
      <select aria-label="Account" name="account" defaultValue={edit?.account}>
        {active.map((a) => (
          <option key={a.id} value={a.id}>
            {a.institution} · {a.name}
          </option>
        ))}
      </select>
    </label>
  );
  const categorySelect = (
    <label>
      Category
      <select
        aria-label="Category"
        name="category"
        defaultValue={edit?.category}
      >
        {categories.map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
    </label>
  );
  const transactionTable = (limit?: number) => (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Transaction</th>
            <th>Category</th>
            <th>Account / source</th>
            <th>Date</th>
            <th className="right">Amount</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {es.slice(0, limit).map((e) => (
            <tr key={e.id}>
              <td>
                <span
                  className={`txicon ${e.kind === "income" ? "positive" : ""}`}
                >
                  {e.kind === "income" ? (
                    <ArrowDownLeft size={17} />
                  ) : (
                    <ArrowUpRight size={17} />
                  )}
                </span>
                <strong>{e.description}</strong>
              </td>
              <td>
                <span className="pill">{e.category}</span>
              </td>
              <td>
                {s.accounts.find((a) => a.id === e.account)?.institution}
                <small>{e.source}</small>
              </td>
              <td>{e.date}</td>
              <td
                className={`right mono ${e.kind === "income" || e.kind === "refund" ? "positive" : ""}`}
              >
                {e.kind === "expense" ? "-" : e.kind === "income" ? "+" : ""}
                {money(e.amount)}
                {e.fee > 0 && <small>Fee {money(e.fee)}</small>}
              </td>
              <td>
                <button
                  className="text"
                  onClick={() => {
                    setEdit(e);
                    open("Transaction");
                  }}
                  aria-label={`Edit ${e.description}`}
                >
                  Edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {es.length === 0 && (
        <div className="empty">
          No transactions in this period. Add your first entry to start seeing
          the bigger picture.
        </div>
      )}
    </div>
  );
  if (!ready)
    return <div className="welcome">Opening your secure workspace…</div>;
  return (
    <div className="app">
      <aside>
        <a className="brand" href="#" onClick={() => setPage("Overview")}>
          <span className="brand-icon">s</span>SALDO
          <span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">PERSONAL WORKSPACE</div>
        <nav>
          {nav.map(([name, Icon]) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              aria-current={page === name ? "page" : undefined}
              onClick={() => {
                setPage(name);
                window.scrollTo(0, 0);
              }}
            >
              <Icon size={19} />
              {name}
              {page === name && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local">
            <ShieldCheck size={19} />
            <div>
              Yours. Always.<small>Local-first. No bank logins.</small>
            </div>
          </div>
          <div className="profile">
            <span className="avatar">S</span>
            <div>
              Personal workspace<small>PHP · Asia/Manila</small>
            </div>
            <Settings size={16} />
          </div>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} /> <strong>{page}</strong>
          </div>
          <div className="header-actions">
            <label className="search">
              <Search size={16} />
              <input
                id="search"
                placeholder="Search transactions"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage("Transactions");
                }}
              />
              <kbd>⌘ K</kbd>
            </label>
            <button
              className="icon"
              aria-label="Toggle privacy"
              onClick={() => setHidden(!hidden)}
            >
              {hidden ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
            <button
              className="icon"
              aria-label="Toggle theme"
              onClick={() => setLight(!light)}
            >
              {light ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <span className="avatar small-avatar">S</span>
          </div>
        </header>
        <div className="content">
          {sample && (
            <div className="sample-banner">
              <span>
                <span className="live-dot" /> SAMPLE WORKSPACE · Session only,
                no real data saved
              </span>
              <button
                className="text"
                onClick={() => {
                  setS(demo());
                  setNotice("Sample data loaded");
                }}
              >
                Load example data ↗
              </button>
            </div>
          )}
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button className="text" onClick={() => setNotice("")}>
                Dismiss
              </button>
            </div>
          )}
          <div className="page-title">
            <div className="min-w-0">
              <div className="eyebrow">PERSONAL FINANCE, IN FOCUS</div>
              <h1>
                {page === "Overview" ? "Your money, in perspective." : page}
              </h1>
              <p>
                {page === "Overview"
                  ? "A clear view of where you are. More confidence in where you’re going."
                  : page === "Calculators"
                    ? "A little planning today. More possibility tomorrow."
                    : page === "Investments"
                      ? "Your watchlist, valuations and a clear view of market data."
                      : "Every detail, working together for your bigger picture."}
              </p>
            </div>
            <button
              className="primary"
              disabled={!active.length || busy}
              onClick={() => {
                setEdit(undefined);
                open("Transaction");
              }}
            >
              <Plus size={17} /> Add transaction
            </button>
          </div>
          {!s.onboarded && page !== "Calculators" && (
            <section className="onboarding panel">
              <ShieldCheck size={32} />
              <div>
                <h2>Welcome to a clearer financial life.</h2>
                <p>
                  Start with an account and its opening balance. PHP, Manila
                  dates, encrypted desktop storage.
                </p>
              </div>
              <button className="primary" onClick={() => open("Account")}>
                Set up your first account <ArrowUpRight size={16} />
              </button>
            </section>
          )}
          {["Overview", "Transactions", "Budgets", "Analytics"].includes(
            page,
          ) && (
            <div className="toolbar">
              <div className="segmented">
                <button className="selected">Monthly view</button>
                <span>PHP · Philippine peso</span>
              </div>
              <div className="filters">
                <select
                  aria-label="Filter accounts"
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  <option value="all">All accounts</option>
                  {s.accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.institution} · {a.name}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Selected month"
                  type="month"
                  value={month}
                  onChange={(e) => e.target.value && setMonth(e.target.value)}
                />
              </div>
            </div>
          )}
          {page === "Overview" && (
            <>
              <div className="stats">
                <section className="stat featured">
                  <div className="stat-label">
                    Total net worth <Wallet size={17} />
                  </div>
                  <div className="stat-value">{money(worth)}</div>
                  <div className="stat-note">
                    <span className="live-dot" /> Calculated from your ledger
                  </div>
                  <div className="stat-decoration" />
                </section>
                {[
                  ["Income", flow.income, "Money coming in"],
                  ["Expenses", flow.expenses, "Your spending this month"],
                  [
                    "Available to earmark",
                    sum([
                      sum(
                        s.accounts
                          .filter(
                            (a) =>
                              ![
                                "credit card",
                                "loan",
                                "other liability",
                                "other asset",
                              ].includes(a.type),
                          )
                          .map((a) => Math.max(0, balance(s, a))),
                      ),
                      -sum(s.goals.map((g) => g.allocated)),
                    ]),
                    "Liquid funds less virtual allocations",
                  ],
                ].map(([title, value, note]) => (
                  <section className="stat" key={title}>
                    <div className="stat-label">
                      {title}
                      <ArrowUpRight size={17} />
                    </div>
                    <div className="stat-value">{money(Number(value))}</div>
                    <div className="stat-note">{note}</div>
                  </section>
                ))}
              </div>
              <button
                className="planning-shortcut"
                onClick={() => setPage("Calculators")}
              >
                <span className="tool-icon">
                  <Calculator size={20} />
                </span>
                <span>
                  <strong>Your next move starts with a plan.</strong>
                  <small>
                    Explore loans, savings, and the milestones ahead.
                  </small>
                </span>
                <span className="planning-link">
                  Open calculators <ArrowUpRight size={17} />
                </span>
              </button>
              <div className="dashboard-grid">
                <section className="panel chart-panel">
                  <div className="panel-head">
                    <div>
                      <h2>Your wealth over time</h2>
                      <p>Month-end ledger balances · PHP</p>
                    </div>
                    <span className="legend-dot">Net worth</span>
                  </div>
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trend}>
                        <defs>
                          <linearGradient
                            id="green"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#5bd5ab"
                              stopOpacity={0.25}
                            />
                            <stop
                              offset="100%"
                              stopColor="#5bd5ab"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid vertical={false} stroke="var(--line)" />
                        <XAxis
                          dataKey="month"
                          axisLine={false}
                          tickLine={false}
                          stroke="#81938c"
                          fontSize={11}
                        />
                        <YAxis
                          hide={hidden}
                          axisLine={false}
                          tickLine={false}
                          stroke="#81938c"
                          fontSize={11}
                          tickFormatter={(n) => `${n / 1000}k`}
                        />
                        <Tooltip
                          formatter={(v) =>
                            hidden ? "Hidden" : money(Number(v) * 100)
                          }
                          contentStyle={{
                            background: "var(--surface)",
                            border: "1px solid var(--line)",
                            borderRadius: 10,
                          }}
                        />
                        <Area
                          isAnimationActive={false}
                          type="monotone"
                          dataKey="worth"
                          stroke="#63d6af"
                          fill="url(#green)"
                          strokeWidth={2.5}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="chart-foot">
                    <ShieldCheck size={14} /> Recorded balances only. No
                    forecast or simulated growth.
                  </div>
                </section>
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Your accounts</h2>
                      <p>One place for every peso</p>
                    </div>
                    <button
                      className="text"
                      onClick={() => setPage("Accounts")}
                    >
                      View all ↗
                    </button>
                  </div>
                  <div className="account-list">
                    {active.slice(0, 4).map((a, i) => (
                      <div className="account-row" key={a.id}>
                        <span className={`institution color-${i % 5}`}>
                          {a.institution.slice(0, 2)}
                        </span>
                        <div>
                          <strong>{a.institution}</strong>
                          <small>{a.name}</small>
                        </div>
                        <div className="account-balance">
                          {money(balance(s, a))}
                          <small>Manual ledger</small>
                        </div>
                      </div>
                    ))}
                    {!active.length && (
                      <div className="empty">
                        Your accounts will appear here.
                      </div>
                    )}
                  </div>
                  <button
                    className="add-account"
                    onClick={() => open("Account")}
                  >
                    <Plus size={16} /> Connect your picture · Add account
                  </button>
                </section>
              </div>
              <div className="dashboard-grid bottom-grid">
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Recent activity</h2>
                      <p>The little things behind the big picture</p>
                    </div>
                    <button
                      className="text"
                      onClick={() => setPage("Transactions")}
                    >
                      All transactions ↗
                    </button>
                  </div>
                  {transactionTable(4)}
                </section>
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Ahead of the curve</h2>
                      <p>Your budget, at a glance</p>
                    </div>
                    <PiggyBank size={20} />
                  </div>
                  {s.budgets
                    .filter((b) => b.month === month)
                    .slice(0, 3)
                    .map((b, i) => (
                      <div className="budget-mini" key={b.id}>
                        <div>
                          <strong>{b.category}</strong>
                          <span>
                            {Math.round(
                              (spent(s, b.category, month) / b.limit) * 100,
                            )}
                            %
                          </span>
                        </div>
                        <progress
                          className={`progress-${i}`}
                          value={Math.max(0, spent(s, b.category, month))}
                          max={b.limit}
                        />
                        <small>
                          {money(spent(s, b.category, month))} of{" "}
                          {money(b.limit)}
                        </small>
                      </div>
                    ))}
                  {!s.budgets.length && (
                    <div className="empty">
                      Give your spending a little direction.
                      <button className="text" onClick={() => open("Budget")}>
                        Create a budget ↗
                      </button>
                    </div>
                  )}
                </section>
              </div>
            </>
          )}
          {page === "Accounts" && (
            <>
              <div className="section-actions">
                <h2>Accounts & balances</h2>
                <button
                  onClick={() => open("Reconcile")}
                  disabled={!active.length}
                >
                  Verify a balance
                </button>
                <button className="primary" onClick={() => open("Account")}>
                  <Plus size={16} /> Add account
                </button>
              </div>
              <div className="cards">
                {s.accounts.map((a, i) => (
                  <section className="panel account-card" key={a.id}>
                    <div className="panel-head">
                      <span className={`institution color-${i % 5}`}>
                        {a.institution.slice(0, 2)}
                      </span>
                      <span className="pill">{a.type}</span>
                    </div>
                    <h2>{a.institution}</h2>
                    <p>
                      {a.name} {a.archived ? "· Archived" : ""}
                    </p>
                    <div className="stat-value">{money(balance(s, a))}</div>
                    <p>
                      Opening {money(a.opening)} · {a.opened}
                    </p>
                    <small>Manual ledger · Real-time sync unavailable</small>
                    <div className="row-actions">
                      <button
                        className="text"
                        onClick={() => {
                          setEditAccount(a);
                          setError("");
                          setModal("Account");
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="text"
                        onClick={() =>
                          void apply("Account inclusion", (n) => {
                            n.accounts.find((x) => x.id === a.id)!.include =
                              !a.include;
                          })
                        }
                      >
                        {a.include ? "Included in" : "Excluded from"} net worth
                      </button>
                      <button
                        className="text"
                        onClick={() =>
                          void apply("Account archive", (n) => {
                            n.accounts.find((x) => x.id === a.id)!.archived =
                              !a.archived;
                          })
                        }
                      >
                        {a.archived ? "Restore" : "Archive"}
                      </button>
                    </div>
                    {s.snapshots
                      .filter((x) => x.account === a.id)
                      .slice(-1)
                      .map((x) => {
                        const difference = x.actual - balance(s, a, x.date);
                        return (
                          <div className="snapshot" key={x.id}>
                            Verified {money(x.actual)} on {x.date}
                            <br />
                            Difference {money(difference)}
                            {difference !== 0 && (
                              <button
                                onClick={() => {
                                  if (
                                    confirm(
                                      `Post an audited adjustment of ${money(difference)}?`,
                                    )
                                  )
                                    void apply(
                                      "Reconciliation adjustment",
                                      (n) => {
                                        n.entries.push({
                                          id: id(),
                                          date: x.date,
                                          description:
                                            "Explicit reconciliation adjustment",
                                          kind: "adjustment",
                                          account: a.id,
                                          amount: difference,
                                          fee: 0,
                                          category: "Miscellaneous",
                                          source: "reconciliation",
                                        });
                                      },
                                    );
                                }}
                              >
                                Review & post adjustment
                              </button>
                            )}
                          </div>
                        );
                      })}
                  </section>
                ))}
              </div>
            </>
          )}
          {page === "Transactions" && (
            <section className="panel">
              <div className="panel-head">
                <div>
                  <h2>Transaction ledger</h2>
                  <p>{es.length} entries · Transfers excluded from cash flow</p>
                </div>
                <div className="row-actions">
                  <button
                    onClick={() => open("Import")}
                    disabled={!active.length}
                  >
                    <Upload size={15} /> Import CSV
                  </button>
                  <button onClick={exportCSV}>
                    <Download size={15} /> Export CSV
                  </button>
                </div>
              </div>
              {transactionTable()}
            </section>
          )}
          {page === "Budgets" && (
            <>
              <div className="section-actions">
                <h2>A plan for your money</h2>
                <button className="primary" onClick={() => open("Budget")}>
                  <Plus size={16} /> Create budget
                </button>
              </div>
              <div className="cards">
                {s.budgets
                  .filter((b) => b.month === month)
                  .map((b) => {
                    const value = spent(s, b.category, month);
                    return (
                      <section className="panel account-card" key={b.id}>
                        <h2>{b.category}</h2>
                        <div className="stat-value">
                          {money(b.limit - value)}
                        </div>
                        <p>remaining of {money(b.limit)}</p>
                        <progress value={Math.max(0, value)} max={b.limit} />
                        <p>
                          {money(value)} spent ·{" "}
                          {Math.round((value / b.limit) * 100)}% used
                        </p>
                        {value >= b.limit * 0.8 && (
                          <div className="insight">
                            {value > b.limit
                              ? "Over budget"
                              : "Approaching your limit"}{" "}
                            · Based on posted expenses and refunds.
                          </div>
                        )}
                        <button
                          className="text danger"
                          onClick={() => {
                            if (confirm("Delete this budget?"))
                              void apply("Budget removed", (n) => {
                                n.budgets = n.budgets.filter(
                                  (x) => x.id !== b.id,
                                );
                              });
                          }}
                        >
                          Remove budget
                        </button>
                      </section>
                    );
                  })}
              </div>
            </>
          )}
          {page === "Savings" && (
            <>
              <div className="section-actions">
                <div>
                  <h2>Make room for what matters.</h2>
                  <p>
                    Virtual earmarks reserve existing funds; they never create
                    new assets.
                  </p>
                </div>
                <button
                  className="primary"
                  onClick={() => open("Goal")}
                  disabled={!active.length}
                >
                  <Plus size={16} /> New goal
                </button>
              </div>
              <div className="cards">
                {s.goals.map((g) => (
                  <section className="panel account-card" key={g.id}>
                    <Target className="positive" />
                    <h2>{g.name}</h2>
                    <div className="stat-value">{money(g.allocated)}</div>
                    <p>
                      of {money(g.target)} · Target {g.due}
                    </p>
                    <progress value={g.allocated} max={g.target} />
                    <p>
                      {s.accounts.find((a) => a.id === g.account)?.name} ·
                      Virtual earmark
                    </p>
                    <button
                      onClick={() => {
                        const amount = prompt(
                          "New total earmarked amount in PHP",
                          (g.allocated / 100).toFixed(2),
                        );
                        if (amount !== null)
                          try {
                            const n = minor(amount);
                            void apply("Allocation updated", (d) => {
                              d.goals.find((x) => x.id === g.id)!.allocated = n;
                            });
                          } catch (e) {
                            setError(String(e));
                          }
                      }}
                    >
                      Update allocation
                    </button>
                    <button
                      className="text danger"
                      onClick={() => {
                        if (confirm("Remove goal and release its earmark?"))
                          void apply("Goal removed", (n) => {
                            n.goals = n.goals.filter((x) => x.id !== g.id);
                          });
                      }}
                    >
                      Release & remove
                    </button>
                  </section>
                ))}
              </div>
            </>
          )}
          {page === "Calculators" && <Calculators hidden={hidden} />}
          {page === "Investments" && (
            <Investments
              market={s.market}
              sample={sample}
              hidden={hidden}
              persist={persistMarket}
            />
          )}
          {page === "Connections" && (
            <Connections
              canImport={active.length > 0}
              onImport={() => {
                setPage("Transactions");
                open("Import");
              }}
            />
          )}
          {page === "Analytics" && (
            <>
              <div className="stats">
                {[
                  ["Net cash flow", flow.net],
                  ["Income", flow.income],
                  ["Expenses", flow.expenses],
                ].map(([label, n]) => (
                  <section className="stat" key={label}>
                    <div className="stat-label">{label}</div>
                    <div className="stat-value">{money(Number(n))}</div>
                  </section>
                ))}
                <section className="stat">
                  <div className="stat-label">Savings rate</div>
                  <div className="stat-value">
                    {flow.income
                      ? `${Math.round((flow.net / flow.income) * 100)}%`
                      : "—"}
                  </div>
                  <small>Net cash flow / income</small>
                </section>
              </div>
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Income & expenses</h2>
                    <p>Posted entries · Transfers and adjustments excluded</p>
                  </div>
                </div>
                <div className="chart">
                  <ResponsiveContainer>
                    <BarChart data={trend}>
                      <CartesianGrid vertical={false} stroke="var(--line)" />
                      <XAxis dataKey="month" />
                      <YAxis hide={hidden} />
                      <Tooltip
                        formatter={(v) =>
                          hidden ? "Hidden" : money(Number(v) * 100)
                        }
                      />
                      <Legend />
                      <Bar
                        isAnimationActive={false}
                        dataKey="income"
                        fill="#65d8ad"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        isAnimationActive={false}
                        dataKey="expenses"
                        fill="#788b9c"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </>
          )}
          {page === "Settings" && (
            <section className="panel settings">
              <h2>Your workspace, your rules.</h2>
              <div className="setting">
                <div>
                  <strong>Appearance</strong>
                  <p>Choose a comfortable theme for this session.</p>
                </div>
                <button onClick={() => setLight(!light)}>
                  {light ? "Light" : "Dark"} mode
                </button>
              </div>
              <div className="setting">
                <div>
                  <strong>Storage & security</strong>
                  <p>
                    {desktop
                      ? "SQLCipher encrypted database · OS keychain-managed key."
                      : "Browser sample mode · Memory only. Install the desktop app for encrypted persistence."}
                  </p>
                  <p>
                    Lost OS keychain access may make your data unrecoverable.
                    Backup/restore and app lock are not yet available.
                  </p>
                </div>
                <ShieldCheck />
              </div>
              <div className="setting">
                <div>
                  <strong>Currency & integrations</strong>
                  <p>
                    PHP ledger · Asia/Manila · Optional Finnhub quotes · No bank
                    sync or telemetry.
                  </p>
                </div>
              </div>
              <div className="setting">
                <div>
                  <strong>Sample workspace</strong>
                  <p>
                    Separate memory-only dataset. Switching back reloads your
                    desktop database.
                  </p>
                </div>
                <button
                  onClick={async () => {
                    if (sample) {
                      setS(await load());
                      setSample(!desktop);
                    } else {
                      setSample(true);
                      setS(demo());
                    }
                  }}
                >
                  {sample ? "Reset / return" : "Open sample mode"}
                </button>
              </div>
              <div className="setting">
                <div>
                  <strong>Export transactions</strong>
                  <p>CSV exports contain plaintext financial data.</p>
                </div>
                <button onClick={exportCSV}>Export CSV</button>
              </div>
              <button onClick={() => setPage("Connections")}>
                Bank and wallet connections
              </button>
              <h2>Audit trail</h2>
              {s.audit
                .slice(-12)
                .reverse()
                .map((a, i) => (
                  <div className="audit" key={i}>
                    <span>{a.action}</span>
                    <small>{a.at}</small>
                  </div>
                ))}
            </section>
          )}
          <footer>
            <span>
              <ShieldCheck size={13} />{" "}
              {desktop && !sample
                ? "Encrypted on this device"
                : "Session-only sample"}{" "}
              · Your money stays yours.
            </span>
            <span>SALDO / 0.3.0</span>
          </footer>
        </div>
      </main>
      {modal && (
        <div className="modal-backdrop" onClick={() => setModal("")}>
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            className="modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-head">
              <h2 id="dialog-title">
                {edit && modal === "Transaction"
                  ? "Edit transaction"
                  : modal === "Import"
                    ? "Import transactions"
                    : modal}
              </h2>
              <button
                className="icon"
                aria-label="Close dialog"
                onClick={() => setModal("")}
              >
                <X size={20} />
              </button>
            </div>
            {error && (
              <div className="alert" role="alert">
                {error}
              </div>
            )}
            <form onSubmit={submit}>
              {modal === "Account" && (
                <>
                  {field("Account nickname", "name", "text", editAccount?.name)}
                  <label>
                    Institution
                    <select
                      aria-label="Institution"
                      name="institution"
                      defaultValue={editAccount?.institution}
                    >
                      {presets.map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Account type
                    <select
                      aria-label="Account type"
                      name="type"
                      defaultValue={editAccount?.type}
                    >
                      {[
                        "savings",
                        "e-wallet",
                        "cash",
                        "checking",
                        "investment cash",
                        "credit card",
                        "loan",
                        "other asset",
                        "other liability",
                      ].map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                  {field(
                    "Opening balance (PHP; debt is negative)",
                    "opening",
                    "text",
                    editAccount
                      ? (editAccount.opening / 100).toFixed(2)
                      : "0.00",
                  )}
                  {field(
                    "Opening date",
                    "date",
                    "date",
                    editAccount?.opened || today(),
                  )}
                  <p>
                    Import only entries on or after this date, excluding any
                    already included in the opening balance. Presets are labels,
                    not integrations.
                  </p>
                </>
              )}
              {modal === "Transaction" && (
                <>
                  {field(
                    "Description",
                    "description",
                    "text",
                    edit?.description,
                  )}
                  <label>
                    Type
                    <select
                      aria-label="Type"
                      name="kind"
                      defaultValue={edit?.kind}
                    >
                      {[
                        "expense",
                        "income",
                        "refund",
                        "transfer",
                        "adjustment",
                      ].map((k) => (
                        <option key={k}>{k}</option>
                      ))}
                    </select>
                  </label>
                  {accountsSelect}
                  <label>
                    Transfer destination (used for transfers only)
                    <select
                      aria-label="Transfer destination"
                      name="to"
                      defaultValue={edit?.to}
                    >
                      {active.map((a) => (
                        <option value={a.id} key={a.id}>
                          {a.institution} · {a.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {field(
                    "Amount (PHP)",
                    "amount",
                    "text",
                    edit ? (edit.amount / 100).toFixed(2) : undefined,
                  )}
                  {field(
                    "Separate fee (PHP)",
                    "fee",
                    "text",
                    edit ? (edit.fee / 100).toFixed(2) : "0.00",
                  )}
                  {categorySelect}
                  {field("Date", "date", "date", edit?.date || today())}
                  <p>
                    Transfers are cash-flow neutral. Fees are separate expenses
                    under Bills. Adjustments affect net worth, not income.
                  </p>
                </>
              )}
              {modal === "Budget" && (
                <>
                  {categorySelect}
                  {field("Monthly spending limit (PHP)", "amount")}
                  <p>
                    Budget period: {month}. Expenses less refunds; transfers
                    excluded. Fees belong to Bills.
                  </p>
                </>
              )}
              {modal === "Goal" && (
                <>
                  {field("Goal name", "name")}
                  {field("Target amount (PHP)", "amount")}
                  {accountsSelect}
                  {field(
                    "Earmark existing funds (PHP)",
                    "allocated",
                    "text",
                    "0.00",
                  )}
                  {field("Target date", "date", "date", today())}
                  <p>
                    This allocation reserves existing account funds. It does not
                    move money or add to net worth.
                  </p>
                </>
              )}
              {modal === "Reconcile" && (
                <>
                  {accountsSelect}
                  {field("Actual verified balance (PHP)", "amount")}
                  <p>
                    A snapshot records your observation without changing the
                    ledger. Any adjustment requires separate review.
                  </p>
                </>
              )}
              {modal === "Import" && (
                <>
                  <p>
                    Universal CSV: date (YYYY-MM-DD), description, kind, amount,
                    category. Supported kinds: income, expense, refund.
                    Same-value duplicates are skipped.
                  </p>
                  <label>
                    Destination account
                    <select id="import-account">
                      {active.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.institution} · {a.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Choose CSV
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      onChange={async (e) => {
                        setError("");
                        try {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          if (file.size > 2_000_000)
                            throw Error("File exceeds 2 MB");
                          const account = (
                            document.getElementById(
                              "import-account",
                            ) as HTMLSelectElement
                          ).value;
                          const rows = previewCSV(
                            await file.text(),
                            account,
                            s,
                          );
                          validate({ ...s, entries: [...s.entries, ...rows] });
                          setPreview(rows);
                        } catch (e) {
                          setPreview([]);
                          setError(String(e));
                        }
                      }}
                    />
                  </label>
                  <div className="import-preview">
                    {preview.length} new rows
                    {preview.slice(0, 20).map((e) => (
                      <div key={e.id}>
                        {e.date} · {e.description} · {money(e.amount)}
                      </div>
                    ))}
                  </div>
                  <button
                    className="primary"
                    type="button"
                    disabled={!preview.length || busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        const n = importEntries(s, preview);
                        if (!sample) await save(n);
                        setS(n);
                        setPreview([]);
                        setModal("");
                        setNotice("CSV import saved");
                      } catch (e) {
                        setError(String(e));
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Confirm {preview.length} rows
                  </button>
                </>
              )}
              {modal !== "Import" && (
                <div className="form-actions">
                  {edit && modal === "Transaction" && (
                    <button
                      className="danger"
                      type="button"
                      onClick={() => {
                        if (
                          confirm(
                            "Delete this entry? Balances will be recalculated; audit history is retained.",
                          )
                        )
                          void apply("Transaction deleted", (n) => {
                            n.entries = n.entries.filter(
                              (e) => e.id !== edit.id,
                            );
                          });
                      }}
                    >
                      Delete entry
                    </button>
                  )}
                  <button type="button" onClick={() => setModal("")}>
                    Cancel
                  </button>
                  <button disabled={busy} className="primary" type="submit">
                    {busy ? "Saving…" : "Save " + modal.toLowerCase()}
                  </button>
                </div>
              )}
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
