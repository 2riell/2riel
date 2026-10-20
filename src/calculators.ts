import Decimal from "decimal.js";
const D = Decimal.clone({ precision: 40, rounding: Decimal.ROUND_HALF_UP });
const MAX = 9_000_000_000_000_000;
export function cents(value: string, label = "Amount"): number {
  if (!/^\d+(?:\.\d{1,2})?$/.test(value.trim()))
    throw Error(
      `${label}: enter a nonnegative amount with up to two decimals.`,
    );
  const result = new D(value.trim()).mul(100);
  if (result.gt(1_000_000_000_000)) throw Error(`${label} is too large.`);
  return result.toNumber();
}
function integer(value: number, label: string, min = 0, max = MAX) {
  if (!Number.isSafeInteger(value) || value < min || value > max)
    throw Error(`${label} must be between ${min} and ${max}.`);
  return value;
}
export function term(value: string): number {
  if (!/^\d+$/.test(value.trim()))
    throw Error("Enter a whole number of months.");
  return integer(Number(value), "Months", 1, 1200);
}
function rate(value: string, max = 100): Decimal {
  if (!/^\d+(?:\.\d{1,6})?$/.test(value.trim()))
    throw Error("Enter a nonnegative percentage with up to six decimals.");
  const n = new D(value.trim());
  if (n.gt(max)) throw Error(`Percentage must be between 0 and ${max}.`);
  return n;
}
function rounded(n: Decimal, up = false): number {
  if (!n.isFinite() || n.abs().gt(MAX))
    throw Error("Result exceeds the supported amount. Reduce the inputs.");
  return integer(
    n
      .toDecimalPlaces(0, up ? Decimal.ROUND_CEIL : Decimal.ROUND_HALF_UP)
      .toNumber(),
    "Result",
  );
}
function payment(principal: number, monthlyRate: Decimal, months: number) {
  return monthlyRate.isZero()
    ? new D(principal).div(months)
    : new D(principal)
        .mul(monthlyRate)
        .div(new D(1).minus(new D(1).plus(monthlyRate).pow(-months)));
}
export type PaymentRow = {
  month: number;
  payment: number;
  principal: number;
  interest: number;
  balance: number;
};
function repay(
  principal: number,
  monthlyRate: Decimal,
  regular: number,
  maxMonths: number,
  clearLast: boolean,
) {
  let balance = principal,
    totalInterest = 0,
    totalPaid = 0;
  const rows: PaymentRow[] = [];
  for (let month = 1; month <= maxMonths && balance > 0; month++) {
    const interest = rounded(new D(balance).mul(monthlyRate));
    const due = integer(balance + interest, "Payment");
    const paid =
      clearLast && month === maxMonths ? due : Math.min(regular, due);
    if (paid <= interest)
      throw Error(
        "Payment does not cover the monthly interest. Increase your payment.",
      );
    const paidPrincipal = paid - interest;
    balance -= paidPrincipal;
    totalInterest = integer(totalInterest + interest, "Total interest");
    totalPaid = integer(totalPaid + paid, "Total payments");
    rows.push({
      month,
      payment: paid,
      principal: paidPrincipal,
      interest,
      balance,
    });
  }
  if (balance > 0)
    throw Error(
      "This payment takes more than 100 years to repay. Increase the payment.",
    );
  return { rows, totalInterest, totalPaid, months: rows.length };
}
export function loan(input: {
  price: number;
  down: number;
  annualRate: string;
  months: number;
  extra: number;
  fees: number;
}) {
  const { price, down, months, extra, fees } = input;
  [price, down, extra, fees].forEach((v) => integer(v, "Amount"));
  integer(months, "Months", 1, 1200);
  if (down >= price)
    throw Error("Down payment must be less than the purchase or loan amount.");
  const principal = price - down,
    r = rate(input.annualRate).div(1200);
  const regular = Math.max(1, rounded(payment(principal, r, months)));
  const baseline = repay(principal, r, regular, months, true);
  const actual = repay(
    principal,
    r,
    integer(regular + extra, "Monthly payment"),
    months,
    true,
  );
  return {
    ...actual,
    regular,
    principal,
    interestSaved: baseline.totalInterest - actual.totalInterest,
    monthsSaved: baseline.months - actual.months,
    totalCash: integer(actual.totalPaid + down + fees, "Total cash cost"),
  };
}
export function card(
  balance: number,
  monthlyRate: string,
  monthlyPayment: number,
) {
  integer(balance, "Balance", 1);
  integer(monthlyPayment, "Monthly payment", 1);
  return repay(
    balance,
    rate(monthlyRate, 20).div(100),
    monthlyPayment,
    1200,
    false,
  );
}
function growthFactor(r: Decimal, months: number) {
  return new D(1).plus(r).pow(months);
}
function annuityFactor(r: Decimal, months: number) {
  return r.isZero() ? new D(months) : growthFactor(r, months).minus(1).div(r);
}
export function growth(
  initial: number,
  monthly: number,
  annualRate: string,
  months: number,
) {
  integer(initial, "Initial savings");
  integer(monthly, "Monthly contribution");
  integer(months, "Months", 1, 1200);
  const r = rate(annualRate).div(1200),
    rows: { month: number; balance: number; contributed: number }[] = [];
  const stride = Math.max(1, Math.ceil(months / 60));
  for (let m = 0; m <= months; m++) {
    if (m % stride !== 0 && m !== months) continue;
    rows.push({
      month: m,
      balance: rounded(
        new D(initial)
          .mul(growthFactor(r, m))
          .plus(new D(monthly).mul(annuityFactor(r, m))),
      ),
      contributed: integer(initial + monthly * m, "Contributions"),
    });
  }
  const final = rows.at(-1)!;
  return {
    rows,
    balance: final.balance,
    contributed: final.contributed,
    interest: final.balance - final.contributed,
  };
}
export function goal(
  target: number,
  current: number,
  annualRate: string,
  months: number,
) {
  integer(target, "Target", 1);
  integer(current, "Current savings");
  integer(months, "Months", 1, 1200);
  const r = rate(annualRate).div(1200);
  const shortfall = new D(target).minus(
    new D(current).mul(growthFactor(r, months)),
  );
  const monthly = shortfall.lte(0)
    ? 0
    : rounded(shortfall.div(annuityFactor(r, months)), true);
  return { monthly, ...growth(current, monthly, annualRate, months) };
}
export function affordability(
  income: number,
  debts: number,
  ratio: string,
  annualRate: string,
  months: number,
) {
  integer(income, "Monthly income", 1);
  integer(debts, "Existing payments");
  integer(months, "Months", 1, 1200);
  const budget = Math.max(
    0,
    rounded(new D(income).mul(rate(ratio)).div(100)) - debts,
  );
  const r = rate(annualRate).div(1200);
  const capacity = r.isZero()
    ? new D(budget).mul(months)
    : new D(budget).mul(new D(1).minus(new D(1).plus(r).pow(-months))).div(r);
  // Round down: never suggest a principal above the assumed payment budget.
  const principal = integer(capacity.floor().toNumber(), "Loan amount");
  return { budget, principal };
}
export function deposit(
  principal: number,
  annualRate: string,
  days: string,
  withholding: string,
) {
  integer(principal, "Deposit", 1);
  if (!/^\d+$/.test(days.trim()))
    throw Error("Enter a whole number of deposit days.");
  const n = integer(Number(days), "Days", 1, 36500);
  const gross = rounded(
    new D(principal).mul(rate(annualRate)).div(100).mul(n).div(365),
  );
  const tax = rounded(new D(gross).mul(rate(withholding)).div(100));
  return {
    gross,
    tax,
    net: gross - tax,
    maturity: integer(principal + gross - tax, "Maturity value"),
  };
}
export function emergency(
  essential: number,
  months: number,
  current: number,
  monthly: number,
) {
  integer(essential, "Monthly essentials", 1);
  integer(months, "Months of cover", 1, 24);
  integer(current, "Current fund");
  integer(monthly, "Monthly contribution");
  const target = integer(essential * months, "Target"),
    gap = Math.max(0, target - current);
  return {
    target,
    gap,
    monthsToGoal:
      gap === 0 ? 0 : monthly === 0 ? null : Math.ceil(gap / monthly),
  };
}
