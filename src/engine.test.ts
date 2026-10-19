import { describe, it, expect } from "vitest";
import {
  balance,
  cashFlow,
  commit,
  empty,
  importEntries,
  minor,
  netWorth,
  spent,
  validate,
  type Account,
  type Entry,
  type State,
} from "./engine";
import { previewCSV } from "./import";
const a = (
  id: string,
  opening = 10000,
  type: Account["type"] = "savings",
): Account => ({
  id,
  institution: "Cash",
  name: id,
  type,
  currency: "PHP",
  opening,
  opened: "2026-01-01",
  include: true,
  archived: false,
});
const entry = (over: Partial<Entry> = {}): Entry => ({
  id: "e",
  date: "2026-01-10",
  description: "Test",
  kind: "expense",
  account: "a",
  amount: 1000,
  fee: 0,
  category: "Food",
  source: "manual",
  ...over,
});
const state = (): State => ({ ...empty(), accounts: [a("a"), a("b", 0)] });
describe("ledger invariants", () => {
  it("transfers preserve net worth and do not count as expenses", () => {
    const s = state(),
      worth = netWorth(s);
    s.entries = [entry({ kind: "transfer", to: "b" })];
    expect(netWorth(s)).toBe(worth);
    expect(balance(s, s.accounts[0])).toBe(9000);
    expect(balance(s, s.accounts[1])).toBe(1000);
    expect(cashFlow(s, "2026-01-01", "2026-01-31").expenses).toBe(0);
  });
  it("transfer fees reduce net worth once and enter Bills budget", () => {
    const s = state();
    s.entries = [entry({ kind: "transfer", to: "b", fee: 100 })];
    expect(netWorth(s)).toBe(9900);
    expect(spent(s, "Bills", "2026-01")).toBe(100);
    expect(spent(s, "Food", "2026-01")).toBe(0);
    expect(cashFlow(s, "2026-01-01", "2026-01-31").expenses).toBe(100);
  });
  it("edits and deletions recalculate balances and retain audit", () => {
    let s = state();
    s.entries = [entry()];
    s = commit(s, "edit", (d) => {
      d.entries[0].amount = 2000;
    });
    expect(netWorth(s)).toBe(8000);
    s = commit(s, "delete", (d) => {
      d.entries = [];
    });
    expect(netWorth(s)).toBe(10000);
    expect(s.audit).toHaveLength(2);
  });
  it("snapshots do not change calculated balances", () => {
    const s = state();
    s.snapshots = [{ id: "s", account: "a", date: "2026-01-10", actual: 999 }];
    expect(netWorth(s)).toBe(10000);
  });
  it("imports are idempotent", () => {
    const s = state(),
      csv =
        "date,description,kind,amount,category\n2026-01-10,Lunch,expense,10.00,Food";
    const entries = previewCSV(csv, "a", s);
    const once = importEntries(s, entries);
    expect(importEntries(once, entries).entries).toHaveLength(1);
    expect(previewCSV(csv, "a", once)).toHaveLength(0);
  });
  it("credit charges increase debt, repayments are transfers", () => {
    const s = state();
    s.accounts.push(a("card", 0, "credit card"));
    s.entries = [
      entry({ account: "card", amount: 2000 }),
      entry({ id: "p", kind: "transfer", to: "card", amount: 1000 }),
    ];
    expect(balance(s, s.accounts[2])).toBe(-1000);
    expect(netWorth(s)).toBe(8000);
    expect(cashFlow(s, "2026-01-01", "2026-01-31").expenses).toBe(2000);
  });
  it("earmarks reserve money without creating assets", () => {
    const s = state();
    s.goals = [
      {
        id: "g",
        name: "Goal",
        account: "a",
        target: 20000,
        allocated: 5000,
        due: "2026-12-31",
      },
    ];
    expect(netWorth(validate(s))).toBe(10000);
    s.goals[0].allocated = 10001;
    expect(() => validate(s)).toThrow("exceed");
  });
  it("net worth sums included signed asset and liability balances", () => {
    const s = state();
    s.accounts.push(a("loan", -3000, "loan"));
    s.entries = [entry()];
    expect(netWorth(s)).toBe(6000);
  });
  it("rejects mixed currency instead of silently converting", () => {
    const s = state();
    (s.accounts[0] as unknown as { currency: string }).currency = "USD";
    expect(() => validate(s)).toThrow();
  });
  it("money parsing preserves cent precision", () => {
    expect(minor("0.29")).toBe(29);
    expect(minor("-1234.56")).toBe(-123456);
    expect(() => minor("1.001")).toThrow();
    expect(() => minor("1e5")).toThrow();
  });
  it("refunds reduce spending without being income", () => {
    const s = state();
    s.entries = [entry(), entry({ id: "r", kind: "refund", amount: 200 })];
    expect(spent(s, "Food", "2026-01")).toBe(800);
    expect(cashFlow(s, "2026-01-01", "2026-01-31").income).toBe(0);
  });
  it("rejects entries before opening date and self-transfers", () => {
    const s = state();
    s.entries = [entry({ date: "2025-12-31" })];
    expect(() => validate(s)).toThrow("predates");
    s.entries = [entry({ kind: "transfer", to: "a" })];
    expect(() => validate(s)).toThrow("different");
  });
  it("rejects invalid calendar dates, duplicates and fractional cents", () => {
    const s = state();
    s.entries = [entry({ date: "2026-02-30" })];
    expect(() => validate(s)).toThrow();
    s.entries = [entry(), entry()];
    expect(() => validate(s)).toThrow("Duplicate entry");
    s.entries = [entry({ amount: 0.1 })];
    expect(() => validate(s)).toThrow();
  });
});
