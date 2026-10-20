import { useState } from "react";
import {
  ArrowUpRight,
  Calculator,
  CreditCard,
  Download,
  House,
  Landmark,
  RotateCcw,
  ShieldCheck,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import * as calc from "./calculators";
const tools = [
  {
    id: "loan",
    title: "Loan & financing",
    subtitle: "Home, car, personal or education",
    icon: House,
  },
  {
    id: "afford",
    title: "Affordability",
    subtitle: "Find a payment that fits",
    icon: Calculator,
  },
  {
    id: "card",
    title: "Credit card payoff",
    subtitle: "Plan your way out of debt",
    icon: CreditCard,
  },
  {
    id: "growth",
    title: "Compound growth",
    subtitle: "See what consistency can do",
    icon: TrendingUp,
  },
  {
    id: "goal",
    title: "Savings goal",
    subtitle: "Turn a target into a monthly plan",
    icon: Target,
  },
  {
    id: "deposit",
    title: "Time deposit",
    subtitle: "Estimate interest after tax",
    icon: Landmark,
  },
  {
    id: "emergency",
    title: "Emergency fund",
    subtitle: "Build your financial buffer",
    icon: ShieldCheck,
  },
] as const;
type Tool = (typeof tools)[number]["id"];
type Field = { key: string; label: string; unit: string };
const fields: Record<Tool, Field[]> = {
  loan: [
    { key: "price", label: "Purchase / loan amount", unit: "PHP" },
    { key: "down", label: "Down payment", unit: "PHP" },
    { key: "rate", label: "Annual nominal interest", unit: "%" },
    { key: "months", label: "Loan term", unit: "months" },
    { key: "extra", label: "Extra monthly payment", unit: "PHP" },
    { key: "fees", label: "Upfront fees (paid separately)", unit: "PHP" },
  ],
  afford: [
    { key: "income", label: "Monthly take-home income", unit: "PHP" },
    { key: "debts", label: "Existing monthly debt payments", unit: "PHP" },
    { key: "ratio", label: "Maximum share for debt payments", unit: "%" },
    { key: "rate", label: "Annual nominal interest", unit: "%" },
    { key: "months", label: "Loan term", unit: "months" },
  ],
  card: [
    { key: "balance", label: "Outstanding balance", unit: "PHP" },
    { key: "rate", label: "Monthly interest rate", unit: "%" },
    { key: "payment", label: "Fixed monthly payment", unit: "PHP" },
  ],
  growth: [
    { key: "initial", label: "Initial amount", unit: "PHP" },
    { key: "monthly", label: "Monthly contribution", unit: "PHP" },
    { key: "rate", label: "Assumed annual nominal growth", unit: "%" },
    { key: "months", label: "Time horizon", unit: "months" },
  ],
  goal: [
    { key: "target", label: "Target amount", unit: "PHP" },
    { key: "current", label: "Already saved", unit: "PHP" },
    { key: "rate", label: "Assumed annual nominal growth", unit: "%" },
    { key: "months", label: "Time to reach your goal", unit: "months" },
  ],
  deposit: [
    { key: "principal", label: "Deposit amount", unit: "PHP" },
    { key: "rate", label: "Annual interest rate", unit: "%" },
    { key: "days", label: "Deposit term", unit: "days" },
    { key: "tax", label: "Withholding on interest", unit: "%" },
  ],
  emergency: [
    { key: "essential", label: "Monthly essential expenses", unit: "PHP" },
    { key: "months", label: "Months of cover", unit: "months" },
    { key: "current", label: "Current emergency fund", unit: "PHP" },
    { key: "monthly", label: "Monthly contribution", unit: "PHP" },
  ],
};
const defaults: Record<Tool, Record<string, string>> = {
  loan: {
    price: "500000",
    down: "100000",
    rate: "8",
    months: "60",
    extra: "0",
    fees: "0",
  },
  afford: {
    income: "50000",
    debts: "5000",
    ratio: "30",
    rate: "8",
    months: "60",
  },
  card: { balance: "50000", rate: "3", payment: "5000" },
  growth: { initial: "10000", monthly: "5000", rate: "5", months: "120" },
  goal: { target: "250000", current: "25000", rate: "0", months: "24" },
  deposit: { principal: "100000", rate: "4", days: "180", tax: "20" },
  emergency: {
    essential: "25000",
    months: "6",
    current: "30000",
    monthly: "5000",
  },
};
const notes: Record<Tool, string> = {
  loan: "Fixed reducing-balance loan. Annual nominal rate ÷ 12; interest rounded to cents each month. Payments occur at month-end; the final payment is adjusted. Extra payments reduce principal without penalties. Fees are paid upfront, excluded from principal. Insurance, taxes, variable rates and lender-specific charges are excluded. Not a disclosed effective interest rate (EIR).",
  afford:
    "Your chosen debt-payment limit is a planning assumption, not a lending rule or approval. Existing payments are subtracted from that limit. Fixed reducing-balance loan, annual nominal rate ÷ 12. Result excludes down payment, fees, insurance and living expenses; check those separately.",
  card: "Fixed monthly interest on the opening balance, rounded to cents, with one payment at month-end. Assumes no new purchases, fees or missed payments. Actual cards often calculate daily interest; this is a simplified estimate. Enter the monthly rate from your statement, not an annual rate.",
  growth:
    "Fixed nominal annual growth ÷ 12, compounded monthly. Contributions are added at month-end. Rounded only for display, without tax, fees, inflation or market losses. This is an illustrative scenario, not a forecast or a guaranteed investment return.",
  goal: "Fixed nominal annual growth ÷ 12; monthly deposits at month-end. Required contribution is rounded up to the next cent. A 0% assumption avoids relying on investment growth. Taxes, fees, inflation and market losses are excluded.",
  deposit:
    "Simple interest using actual days ÷ 365, paid at maturity, without compounding. Gross interest is rounded to cents, then tax is rounded to cents. The tax field is an editable example, not a determination of your tax obligations. Provider day-count rules and early-withdrawal penalties may differ.",
  emergency:
    "Target = essential monthly expenses × your chosen months of cover. Time to target assumes equal month-end contributions with no growth or withdrawals. Your chosen coverage is a planning assumption.",
};
export default function Calculators({ hidden }: { hidden: boolean }) {
  const [tool, setTool] = useState<Tool>("loan"),
    [values, setValues] = useState(defaults);
  const v = values[tool],
    selected = tools.find((x) => x.id === tool)!;
  const money = (n: number) =>
    hidden
      ? "₱••••••"
      : new Intl.NumberFormat("en-PH", {
          style: "currency",
          currency: "PHP",
        }).format(n / 100);
  let label = "",
    value = "",
    caption = "",
    error = "";
  let stats: { label: string; value: string }[] = [],
    rows: calc.PaymentRow[] = [],
    chart: { month: number; balance: number; contributed?: number }[] = [];
  const amount = (key: string) =>
    calc.cents(v[key], fields[tool].find((f) => f.key === key)?.label);
  try {
    if (tool === "loan") {
      const r = calc.loan({
        price: amount("price"),
        down: amount("down"),
        annualRate: v.rate,
        months: calc.term(v.months),
        extra: amount("extra"),
        fees: amount("fees"),
      });
      label = "Your monthly payment";
      value = money(r.rows[0].payment);
      caption = `${r.months} payments · Final payment ${money(r.rows.at(-1)!.payment)}`;
      stats = [
        { label: "Amount financed", value: money(r.principal) },
        { label: "Total interest", value: money(r.totalInterest) },
        {
          label: "Total cash incl. down payment & fees",
          value: money(r.totalCash),
        },
        {
          label: "Saved with extra payments",
          value: `${money(r.interestSaved)} · ${r.monthsSaved} months`,
        },
      ];
      rows = r.rows;
    } else if (tool === "card") {
      const r = calc.card(amount("balance"), v.rate, amount("payment"));
      label = "Debt-free in";
      value = `${r.months} months`;
      caption = `With ${money(amount("payment"))} paid each month`;
      stats = [
        { label: "Total interest", value: money(r.totalInterest) },
        { label: "Total repayment", value: money(r.totalPaid) },
        { label: "Final payment", value: money(r.rows.at(-1)!.payment) },
      ];
      rows = r.rows;
    } else if (tool === "growth" || tool === "goal") {
      const months = calc.term(v.months);
      const planned =
        tool === "goal"
          ? calc.goal(amount("target"), amount("current"), v.rate, months)
          : null;
      const r =
        planned ??
        calc.growth(amount("initial"), amount("monthly"), v.rate, months);
      label = tool === "growth" ? "Projected balance" : "Save each month";
      value = money(planned ? planned.monthly : r.balance);
      caption = `Over ${months} months · ${v.rate}% assumed annual nominal growth`;
      stats = [
        { label: "Total contributions", value: money(r.contributed) },
        { label: "Illustrative growth", value: money(r.interest) },
        { label: "Projected final balance", value: money(r.balance) },
      ];
      chart = r.rows;
    } else if (tool === "afford") {
      const r = calc.affordability(
        amount("income"),
        amount("debts"),
        v.ratio,
        v.rate,
        calc.term(v.months),
      );
      label = "Estimated loan capacity";
      value = money(r.principal);
      caption = "Based on your chosen payment limit";
      stats = [
        { label: "Available monthly payment", value: money(r.budget) },
        {
          label: "Debt-payment limit",
          value: `${v.ratio}% of take-home income`,
        },
        { label: "Existing monthly payments", value: money(amount("debts")) },
      ];
    } else if (tool === "deposit") {
      const r = calc.deposit(amount("principal"), v.rate, v.days, v.tax);
      label = "Estimated maturity value";
      value = money(r.maturity);
      caption = `Principal plus net interest after ${v.days} days`;
      stats = [
        { label: "Gross interest", value: money(r.gross) },
        { label: "Withholding on interest", value: money(r.tax) },
        { label: "Net interest earned", value: money(r.net) },
      ];
    } else {
      const months = calc.term(v.months);
      const r = calc.emergency(
        amount("essential"),
        months,
        amount("current"),
        amount("monthly"),
      );
      label = "Your emergency fund target";
      value = money(r.target);
      caption = `${months} months of essential expenses`;
      stats = [
        { label: "Still to save", value: money(r.gap) },
        {
          label: "Time to target",
          value:
            r.monthsToGoal === null
              ? "Set a monthly contribution"
              : r.monthsToGoal === 0
                ? "Target already covered"
                : `${r.monthsToGoal} months`,
        },
        { label: "Already saved", value: money(amount("current")) },
      ];
    }
    if (rows.length)
      chart = [
        { month: 0, balance: rows[0].balance + rows[0].principal },
        ...rows
          .filter(
            (_, i) =>
              i % Math.max(1, Math.ceil(rows.length / 60)) === 0 ||
              i === rows.length - 1,
          )
          .map((r) => ({ month: r.month, balance: r.balance })),
      ];
  } catch (e) {
    error =
      e instanceof Error ? e.message : "Check the inputs to see your estimate.";
  }
  function exportSchedule() {
    const csv =
      "month,payment_php,principal_php,interest_php,balance_php\r\n" +
      rows
        .map((r) =>
          [
            r.month,
            ...[r.payment, r.principal, r.interest, r.balance].map((n) =>
              (n / 100).toFixed(2),
            ),
          ].join(","),
        )
        .join("\r\n");
    const url = URL.createObjectURL(
        new Blob([csv], { type: "text/csv;charset=utf-8" }),
      ),
      link = document.createElement("a");
    link.href = url;
    link.download = `saldo-${tool}-estimate.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <div className="calculator-module">
      <section className="planner-banner">
        <span className="planner-mark">
          <Calculator size={26} />
        </span>
        <div>
          <span className="eyebrow">PLAN BEFORE YOU COMMIT</span>
          <h2>Make the numbers work for you.</h2>
          <p>Explore a payment, build a buffer, or map out your next goal.</p>
        </div>
        <span className="pill">7 essential tools · PHP</span>
      </section>
      <div className="calculator-layout">
        <div
          className="calculator-menu"
          role="group"
          aria-label="Financial calculators"
        >
          {tools.map(({ id, title, subtitle, icon: Icon }) => (
            <button
              key={id}
              aria-pressed={tool === id}
              className={tool === id ? "chosen" : ""}
              onClick={() => setTool(id)}
            >
              <span className="tool-icon">
                <Icon size={20} />
              </span>
              <span>
                <strong>{title}</strong>
                <small>{subtitle}</small>
              </span>
              <ArrowUpRight size={15} />
            </button>
          ))}
        </div>
        <div className="calculator-workspace">
          <section className="panel calculator-inputs">
            <div className="panel-head">
              <div>
                <h2>{selected.title}</h2>
                <p>Edit these example inputs to explore your own scenario.</p>
              </div>
              <button
                className="icon"
                aria-label="Reset calculator examples"
                onClick={() => setValues({ ...values, [tool]: defaults[tool] })}
              >
                <RotateCcw size={16} />
              </button>
            </div>
            <div className="calculator-fields">
              {fields[tool].map((f) => (
                <label key={`${tool}-${f.key}`}>
                  {f.label}
                  <span className="input-with-unit">
                    <input
                      aria-label={f.label}
                      type={hidden && f.unit === "PHP" ? "password" : "text"}
                      inputMode={
                        f.unit === "months" || f.unit === "days"
                          ? "numeric"
                          : "decimal"
                      }
                      autoComplete="off"
                      value={v[f.key]}
                      onChange={(e) =>
                        setValues({
                          ...values,
                          [tool]: { ...v, [f.key]: e.target.value },
                        })
                      }
                    />
                    <span>{f.unit}</span>
                  </span>
                </label>
              ))}
            </div>
            <div className="calculator-foot">
              <ShieldCheck size={14} /> Calculated on your device. These inputs
              stay in this session.
            </div>
          </section>
          <section
            className="panel calculator-result"
            aria-label="Calculator result"
          >
            {error ? (
              <div className="calculator-invalid" role="status">
                <Calculator size={28} />
                <h2>Let’s check the numbers.</h2>
                <p>{error}</p>
              </div>
            ) : (
              <>
                <div className="result-hero">
                  <span className="eyebrow">YOUR ESTIMATE</span>
                  <div className="result-label">{label}</div>
                  <div className="result-value">{value}</div>
                  <p>{caption}</p>
                  <span className="result-decoration" />
                </div>
                <div className="result-metrics">
                  {stats.map((s) => (
                    <div key={s.label}>
                      <small>{s.label}</small>
                      <strong>{s.value}</strong>
                    </div>
                  ))}
                </div>
                {chart.length > 0 && !hidden && (
                  <div className="calculator-chart">
                    <div className="chart-heading">
                      <h2>
                        {rows.length
                          ? "Your path to zero"
                          : "Your savings over time"}
                      </h2>
                      <small>Month · PHP</small>
                    </div>
                    <ResponsiveContainer width="100%" height={190}>
                      <AreaChart data={chart}>
                        <defs>
                          <linearGradient
                            id="calculatorFill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="var(--green)"
                              stopOpacity={0.3}
                            />
                            <stop
                              offset="100%"
                              stopColor="var(--green)"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid vertical={false} stroke="var(--line)" />
                        <XAxis
                          dataKey="month"
                          tickLine={false}
                          axisLine={false}
                          fontSize={11}
                          stroke="var(--muted)"
                        />
                        <YAxis
                          tickFormatter={(n) => `${n / 100000}k`}
                          tickLine={false}
                          axisLine={false}
                          width={55}
                          fontSize={11}
                          stroke="var(--muted)"
                        />
                        <Tooltip
                          formatter={(v) => money(Number(v))}
                          labelFormatter={(v) => `Month ${v}`}
                          contentStyle={{
                            background: "var(--surface)",
                            border: "1px solid var(--line)",
                            borderRadius: 12,
                          }}
                        />
                        <Area
                          name="Balance"
                          type="monotone"
                          dataKey="balance"
                          stroke="var(--green)"
                          fill="url(#calculatorFill)"
                          strokeWidth={2.5}
                          isAnimationActive={false}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
                {rows.length > 0 && (
                  <details className="schedule">
                    <summary>
                      View repayment schedule{" "}
                      <span>{rows.length} payments</span>
                    </summary>
                    <div className="schedule-actions">
                      <small>Estimates in PHP · Month-end payments</small>
                      <button disabled={hidden} onClick={exportSchedule}>
                        <Download size={14} /> Export CSV
                      </button>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Month</th>
                            <th className="right">Payment</th>
                            <th className="right">Principal</th>
                            <th className="right">Interest</th>
                            <th className="right">Remaining</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((r) => (
                            <tr key={r.month}>
                              <td>{r.month}</td>
                              {[
                                r.payment,
                                r.principal,
                                r.interest,
                                r.balance,
                              ].map((n, i) => (
                                <td className="right mono" key={i}>
                                  {money(n)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </>
            )}
          </section>
          <section className="calculator-assumptions">
            <h2>How this estimate works</h2>
            <p>{notes[tool]}</p>
            <small>
              Example rates and inputs are editable assumptions. Calculators do
              not read or change your accounts, investments, budgets or ledger.
            </small>
          </section>
        </div>
      </div>
    </div>
  );
}
