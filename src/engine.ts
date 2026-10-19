import { z } from "zod";
import { emptyMarket, marketSchema } from "./market";
export const presets = [
  "GCash",
  "MariBank",
  "GoTyme",
  "BPI",
  "Maya",
  "CIMB",
  "UnionBank",
  "RCBC",
  "Cash Wallet",
  "Investment Brokerage",
  "Custom Account",
];
export const categories = [
  "Food",
  "Transportation",
  "Shopping",
  "Tuition",
  "Bills",
  "Entertainment",
  "Allowance",
  "Salary",
  "Interest",
  "Miscellaneous",
];
const cents = z.number().int().safe();
const date = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine(
    (s) =>
      !isNaN(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s,
    "Invalid date",
  );
export const accountSchema = z.object({
  id: z.string().min(1),
  name: z.string().trim().min(1).max(100),
  institution: z.string(),
  type: z.enum([
    "cash",
    "savings",
    "checking",
    "e-wallet",
    "investment cash",
    "credit card",
    "loan",
    "other asset",
    "other liability",
  ]),
  opening: cents,
  opened: date,
  currency: z.literal("PHP"),
  include: z.boolean(),
  archived: z.boolean(),
});
export const entrySchema = z.object({
  id: z.string().min(1),
  date,
  description: z.string().trim().min(1).max(200),
  kind: z.enum(["income", "expense", "refund", "transfer", "adjustment"]),
  account: z.string(),
  to: z.string().optional(),
  amount: cents,
  fee: cents.nonnegative(),
  category: z.string(),
  source: z.enum(["manual", "csv", "reconciliation"]),
  importKey: z.string().optional(),
});
export const stateSchema = z.object({
  market: marketSchema.default(emptyMarket),
  revision: z.number().int().nonnegative(),
  onboarded: z.boolean(),
  accounts: z.array(accountSchema),
  entries: z.array(entrySchema),
  budgets: z.array(
    z.object({
      id: z.string(),
      category: z.string(),
      limit: cents.positive(),
      month: z.string().regex(/^\d{4}-\d{2}$/),
    }),
  ),
  goals: z.array(
    z.object({
      id: z.string(),
      name: z.string().min(1),
      target: cents.positive(),
      account: z.string(),
      allocated: cents.nonnegative(),
      due: date,
    }),
  ),
  snapshots: z.array(
    z.object({ id: z.string(), account: z.string(), date, actual: cents }),
  ),
  audit: z.array(z.object({ at: z.string(), action: z.string() })),
});
export type Account = z.infer<typeof accountSchema>;
export type Entry = z.infer<typeof entrySchema>;
export type State = z.infer<typeof stateSchema>;
export const empty = (): State => ({
  market: emptyMarket(),
  revision: 0,
  onboarded: false,
  accounts: [],
  entries: [],
  budgets: [],
  goals: [],
  snapshots: [],
  audit: [],
});
export const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const id = () => crypto.randomUUID();
export function minor(s: string) {
  if (!/^-?\d+(\.\d{1,2})?$/.test(s.trim()))
    throw Error("Use a monetary amount with at most two decimal places.");
  const neg = s.trim().startsWith("-");
  const [a, b = ""] = s.trim().replace("-", "").split(".");
  const n = BigInt(a) * 100n + BigInt(b.padEnd(2, "0"));
  if (n > 9000000000000000n) throw Error("Amount too large");
  return Number(neg ? -n : n);
}
export function sum(ns: number[]) {
  const n = ns.reduce((a, b) => a + BigInt(b), 0n);
  if (
    n > BigInt(Number.MAX_SAFE_INTEGER) ||
    n < BigInt(Number.MIN_SAFE_INTEGER)
  )
    throw Error("Ledger exceeds supported precision");
  return Number(n);
}
export function movement(e: Entry, a: string) {
  return sum([
    e.account === a
      ? e.kind === "expense" || e.kind === "transfer"
        ? -e.amount
        : e.amount
      : 0,
    e.kind === "transfer" && e.to === a ? e.amount : 0,
    e.account === a ? -e.fee : 0,
  ]);
}
export function balance(s: State, a: Account, until = today()) {
  return sum([
    a.opened <= until ? a.opening : 0,
    ...s.entries.filter((e) => e.date <= until).map((e) => movement(e, a.id)),
  ]);
}
export function netWorth(s: State, until?: string) {
  return sum(
    s.accounts.filter((a) => a.include).map((a) => balance(s, a, until)),
  );
}
export function cashFlow(s: State, start: string, end: string) {
  const es = s.entries.filter((e) => e.date >= start && e.date <= end);
  const income = sum(
    es.filter((e) => e.kind === "income").map((e) => e.amount),
  );
  const expenses = sum(
    es.map((e) =>
      sum([
        e.kind === "expense" ? e.amount : e.kind === "refund" ? -e.amount : 0,
        e.fee,
      ]),
    ),
  );
  return { income, expenses, net: sum([income, -expenses]) };
}
export function spent(s: State, category: string, month: string) {
  return sum(
    s.entries
      .filter((e) => e.date.startsWith(month))
      .map((e) =>
        sum([
          e.category === category
            ? e.kind === "expense"
              ? e.amount
              : e.kind === "refund"
                ? -e.amount
                : 0
            : 0,
          category === "Bills" ? e.fee : 0,
        ]),
      ),
  );
}
export function validate(input: State): State {
  const s = stateSchema.parse(input);
  const ids = new Set(s.accounts.map((a) => a.id));
  if (ids.size !== s.accounts.length) throw Error("Duplicate account");
  if (new Set(s.entries.map((e) => e.id)).size !== s.entries.length)
    throw Error("Duplicate entry");
  const keys = s.entries.flatMap((e) => (e.importKey ? [e.importKey] : []));
  if (new Set(keys).size !== keys.length) throw Error("Duplicate import");
  for (const a of s.accounts)
    if (a.opened > today()) throw Error("Opening date cannot be in the future");
  for (const e of s.entries)
    if (e.date > today())
      throw Error(
        "Use posted dates; recurring future entries are not supported yet",
      );
  for (const a of s.accounts)
    if (
      (a.type === "credit card" ||
        a.type === "loan" ||
        a.type === "other liability") &&
      a.opening > 0
    )
      throw Error("Enter liabilities as negative opening balances");
  for (const e of s.entries) {
    const a = s.accounts.find((a) => a.id === e.account);
    if (!a || e.date < a.opened)
      throw Error("Transaction predates its account opening");
    if (e.kind !== "adjustment" && e.amount <= 0)
      throw Error("Amount must be positive");
    if (
      e.kind === "transfer" &&
      (!e.to || e.to === e.account || !ids.has(e.to))
    )
      throw Error("Choose a different destination account");
    if (
      e.to &&
      e.kind === "transfer" &&
      e.date < s.accounts.find((a) => a.id === e.to)!.opened
    )
      throw Error("Transfer predates destination opening");
  }
  for (const g of s.goals) {
    const a = s.accounts.find((a) => a.id === g.account);
    if (!a) throw Error("Goal account missing");
    if (
      sum(
        s.goals.filter((x) => x.account === g.account).map((x) => x.allocated),
      ) > Math.max(0, balance(s, a))
    )
      throw Error("Goal allocations exceed available account funds");
  }
  for (const a of s.accounts) balance(s, a);
  netWorth(s);
  return s;
}
export function commit(
  s: State,
  action: string,
  change: (draft: State) => void,
) {
  const n = structuredClone(s);
  change(n);
  n.revision++;
  n.audit.push({ at: new Date().toISOString(), action });
  return validate(n);
}
export function importEntries(s: State, es: Entry[]) {
  return commit(s, "CSV import", (n) => {
    const keys = new Set(n.entries.map((e) => e.importKey));
    for (const e of es)
      if (!keys.has(e.importKey)) {
        n.entries.push(e);
        keys.add(e.importKey);
      }
  });
}
export function demo(): State {
  const s = empty();
  s.onboarded = true;
  const d = today(),
    month = d.slice(0, 7);
  s.accounts = presets.slice(0, 5).map((institution, i) => ({
    id: `a${i}`,
    institution,
    name: [
      "Daily spending",
      "Rainy day fund",
      "Everyday savings",
      "Payroll",
      "Digital wallet",
    ][i],
    type: i === 0 || i === 4 ? "e-wallet" : "savings",
    opening: [845075, 12500000, 6800000, 4250000, 240000][i],
    opened: `${month}-01`,
    currency: "PHP",
    include: true,
    archived: false,
  }));
  s.entries = [
    ["Salary", "income", "Salary", 6500000, "a3"],
    ["Weekend groceries", "expense", "Food", 248050, "a0"],
    ["Electricity bill", "expense", "Bills", 325000, "a3"],
    ["Coffee & a little catch-up", "expense", "Food", 38500, "a0"],
    ["A ride home", "expense", "Transportation", 24500, "a0"],
  ].map(([description, kind, category, amount, account], i) => ({
    id: `e${i}`,
    date: d,
    description: String(description),
    kind: kind as Entry["kind"],
    category: String(category),
    amount: Number(amount),
    account: String(account),
    fee: 0,
    source: "manual",
  }));
  s.budgets = [
    { id: "b1", category: "Food", limit: 1200000, month },
    { id: "b2", category: "Bills", limit: 1000000, month },
    { id: "b3", category: "Transportation", limit: 400000, month },
  ];
  s.goals = [
    {
      id: "g1",
      name: "A little more peace of mind",
      target: 20000000,
      account: "a1",
      allocated: 10000000,
      due: `${Number(d.slice(0, 4)) + 1}-06-30`,
    },
  ];
  return validate(s);
}
