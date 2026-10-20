import { describe, expect, it } from "vitest";
import {
  affordability,
  card,
  cents,
  deposit,
  emergency,
  goal,
  growth,
  loan,
  term,
} from "./calculators";
describe("financial planning estimates", () => {
  it("parses decimal cents and rejects malformed, unsupported and excessive inputs", () => {
    expect(cents("0.29")).toBe(29);
    expect(cents("100.10")).toBe(10010);
    for (const v of ["", "-1", "1.234", "NaN", "1e3", "9,000", "10000000001"])
      expect(() => cents(v)).toThrow();
    for (const v of ["0", "1.5", "1201", "NaN"])
      expect(() => term(v)).toThrow();
    expect(() => growth(100, 10, "101", 12)).toThrow();
  });
  it("reconciles every amortization row and the entire loan to exact cents", () => {
    const r = loan({
      price: 50000000,
      down: 10000000,
      annualRate: "8",
      months: 60,
      extra: 0,
      fees: 250000,
    });
    expect(r.regular).toBe(811056);
    expect(r.rows).toHaveLength(60);
    expect(r.rows.at(-1)!.balance).toBe(0);
    expect(r.rows.reduce((n, r) => n + r.principal, 0)).toBe(40000000);
    expect(r.totalCash).toBe(r.totalPaid + 10250000);
    let balance = r.principal;
    for (const row of r.rows) {
      expect(row.payment).toBe(row.principal + row.interest);
      expect(row.balance).toBe(balance - row.principal);
      balance = row.balance;
    }
  });
  it("handles zero interest, a final cent adjustment and early repayment without overpayment", () => {
    const r = loan({
      price: 10000,
      down: 0,
      annualRate: "0",
      months: 3,
      extra: 0,
      fees: 0,
    });
    expect(r.rows.map((r) => r.payment)).toEqual([3333, 3333, 3334]);
    expect(r.totalInterest).toBe(0);
    const early = loan({
      price: 10000,
      down: 0,
      annualRate: "12",
      months: 12,
      extra: 100000,
      fees: 0,
    });
    expect(early.rows).toHaveLength(1);
    expect(early.totalPaid).toBe(10100);
    expect(early.interestSaved).toBeGreaterThan(0);
  });
  it("extra payments reduce interest and duration", () => {
    const r = loan({
      price: 10000000,
      down: 0,
      annualRate: "12",
      months: 60,
      extra: 100000,
      fees: 0,
    });
    expect(r.months).toBeLessThan(60);
    expect(r.interestSaved).toBeGreaterThan(0);
    expect(r.monthsSaved).toBe(60 - r.months);
  });
  it("does not invent a payoff date for a payment below interest", () => {
    expect(() => card(10000000, "3", 200000)).toThrow(/interest/);
    const r = card(100000, "0", 30000);
    expect(r.months).toBe(4);
    expect(r.rows.at(-1)!.payment).toBe(10000);
    expect(card(100000, "3", 200000).totalPaid).toBe(103000);
  });
  it("compound growth matches independently calculated annuity values and zero-growth contributions", () => {
    expect(growth(100000, 10000, "0", 12).balance).toBe(220000);
    // 1000*(1.01)^12 + 100*((1.01)^12-1)/0.01 = 2395.07533...
    const r = growth(100000, 10000, "12", 12);
    expect(r.balance).toBe(239508);
    expect(r.interest).toBe(19508);
  });
  it("rounds goal deposits up so the target is reached", () => {
    const r = goal(10000, 0, "0", 3);
    expect(r.monthly).toBe(3334);
    expect(r.balance).toBe(10002);
    const withGrowth = goal(1000000, 200000, "5", 24);
    expect(withGrowth.balance).toBeGreaterThanOrEqual(1000000);
    expect(
      growth(200000, withGrowth.monthly - 1, "5", 24).balance,
    ).toBeLessThan(1000000);
    expect(goal(10000, 20000, "0", 12).monthly).toBe(0);
  });
  it("affordability respects existing debt and the chosen payment cap", () => {
    expect(affordability(5000000, 500000, "30", "0", 60)).toEqual({
      budget: 1000000,
      principal: 60000000,
    });
    expect(affordability(5000000, 2000000, "30", "8", 60)).toEqual({
      budget: 0,
      principal: 0,
    });
  });
  it("time-deposit simple actual/365 interest and tax reconcile", () => {
    const r = deposit(10000000, "4", "180", "20");
    expect(r.gross).toBe(197260);
    expect(r.tax).toBe(39452);
    expect(r.net).toBe(157808);
    expect(r.maturity).toBe(10157808);
  });
  it("emergency fund handles covered targets and absent contributions", () => {
    expect(emergency(2500000, 6, 3000000, 500000)).toEqual({
      target: 15000000,
      gap: 12000000,
      monthsToGoal: 24,
    });
    expect(emergency(10000, 3, 0, 0).monthsToGoal).toBeNull();
    expect(emergency(10000, 3, 40000, 0).monthsToGoal).toBe(0);
  });
});
