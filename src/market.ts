import { z } from "zod";
const fixed = z.number().int().min(0).max(1_000_000_000_000);
export const quoteSchema = z.object({
  symbol: z.string().regex(/^[A-Z][A-Z0-9]{0,9}(?:[.-][AB])?$/),
  priceMicros: fixed.positive(),
  previousCloseMicros: fixed.nullable(),
  timestamp: z.number().int().positive(),
  receivedAt: z.string().datetime(),
  provider: z.enum(["finnhub", "manual"]),
});
function validPostedDate(value: string) {
  return (
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    !isNaN(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value &&
    value <=
      new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Manila",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date())
  );
}
export const purchaseSchema = z
  .object({
    id: z.string().min(1),
    date: z
      .string()
      .refine(
        validPostedDate,
        "Use a valid purchase date that is not in the future",
      ),
    entryMode: z.enum(["amount", "units"]),
    priceMicros: fixed.positive(),
    unitsMicros: fixed.positive(),
    amountUsdMinor: z
      .number()
      .int()
      .positive()
      .safe()
      .max(9_000_000_000_000_000),
    feeUsdMinor: z
      .number()
      .int()
      .nonnegative()
      .safe()
      .max(9_000_000_000_000_000),
  })
  .superRefine((lot, ctx) => {
    try {
      const expected =
        lot.entryMode === "amount"
          ? unitsForAmount(lot.amountUsdMinor, lot.priceMicros)
          : roundRatio(
              BigInt(lot.unitsMicros) * BigInt(lot.priceMicros),
              10_000_000_000n,
            );
      if (
        (lot.entryMode === "amount" ? lot.unitsMicros : lot.amountUsdMinor) !==
        expected
      )
        ctx.addIssue({
          code: "custom",
          message: "Purchase amount, price and quantity do not match",
        });
    } catch (e) {
      ctx.addIssue({
        code: "custom",
        message: e instanceof Error ? e.message : "Invalid purchase",
      });
    }
  });
export type Purchase = z.infer<typeof purchaseSchema>;
export const positionSchema = z
  .object({
    id: z.string().min(1),
    symbol: z.string().regex(/^[A-Z][A-Z0-9]{0,9}(?:[.-][AB])?$/),
    name: z.string().trim().min(1).max(100),
    unitsMicros: fixed,
    costBasisUsdMinor: z.number().int().nonnegative().safe().nullable(),
    quote: quoteSchema.nullable(),
    purchases: z.array(purchaseSchema).max(200).default([]),
  })
  .superRefine((p, ctx) => {
    if (!p.purchases.length) return;
    try {
      const totals = purchaseTotals(p.purchases);
      if (
        new Set(p.purchases.map((l) => l.id)).size !== p.purchases.length ||
        totals.unitsMicros !== p.unitsMicros ||
        totals.costBasisUsdMinor !== p.costBasisUsdMinor
      )
        ctx.addIssue({
          code: "custom",
          message: "Position totals must match its unique purchase records",
        });
    } catch (e) {
      ctx.addIssue({
        code: "custom",
        message: e instanceof Error ? e.message : "Invalid purchases",
      });
    }
  });
export const marketSchema = z
  .object({
    enabled: z.boolean(),
    autoRefresh: z.boolean(),
    positions: z.array(positionSchema).max(10),
    fx: z
      .object({
        rateMicros: fixed.positive(),
        date: z
          .string()
          .regex(/^\d{4}-\d{2}-\d{2}$/)
          .refine(
            (s) =>
              !isNaN(Date.parse(s)) &&
              new Date(s).toISOString().slice(0, 10) === s,
          ),
      })
      .nullable(),
  })
  .superRefine((m, ctx) => {
    if (new Set(m.positions.map((p) => p.symbol)).size !== m.positions.length)
      ctx.addIssue({
        code: "custom",
        message: "Each ticker can appear only once",
      });
    if (new Set(m.positions.map((p) => p.id)).size !== m.positions.length)
      ctx.addIssue({ code: "custom", message: "Duplicate position ID" });
    for (const p of m.positions)
      if (p.quote && p.quote.symbol !== p.symbol)
        ctx.addIssue({
          code: "custom",
          message: "Quote ticker does not match position",
        });
    if (
      m.fx &&
      m.fx.date >
        new Intl.DateTimeFormat("en-CA", {
          timeZone: "Asia/Manila",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }).format(new Date())
    )
      ctx.addIssue({
        code: "custom",
        message: "Exchange-rate date cannot be in the future",
      });
    try {
      marketTotals(m);
    } catch (e) {
      ctx.addIssue({ code: "custom", message: String(e) });
    }
  });
export type Quote = z.infer<typeof quoteSchema>;
export type Position = z.infer<typeof positionSchema>;
export type Market = z.infer<typeof marketSchema>;
export const emptyMarket = (): Market => ({
  enabled: false,
  autoRefresh: false,
  positions: [],
  fx: null,
});
export function scaled(s: string) {
  if (!/^\d+(\.\d{1,6})?$/.test(s.trim()))
    throw Error("Use a nonnegative decimal with up to 6 places");
  const [a, b = ""] = s.trim().split(".");
  const n = BigInt(a) * 1_000_000n + BigInt(b.padEnd(6, "0"));
  if (n > 1_000_000_000_000n) throw Error("Value exceeds supported precision");
  return Number(n);
}
export function unscale(n: number) {
  return `${Math.floor(n / 1_000_000)}.${String(n % 1_000_000).padStart(6, "0")}`.replace(
    /\.?0+$/,
    "",
  );
}
function checked(n: bigint) {
  if (n > 9_000_000_000_000_000n || n < -9_000_000_000_000_000n)
    throw Error("Valuation exceeds supported precision");
  return Number(n);
}
export function roundRatio(n: bigint, d: bigint) {
  if (n < 0n || d <= 0n) throw Error("Invalid valuation ratio");
  return checked((n + d / 2n) / d);
}
export function positionValue(p: Position) {
  return p.quote
    ? roundRatio(
        BigInt(p.unitsMicros) * BigInt(p.quote.priceMicros),
        10_000_000_000n,
      )
    : null;
}
export function toPhp(usdMinor: number, fx: Market["fx"]) {
  return fx
    ? roundRatio(BigInt(usdMinor) * BigInt(fx.rateMicros), 1_000_000n)
    : null;
}
export function marketTotals(m: Market) {
  const valued = m.positions.filter((p) => p.quote);
  const usd = checked(
    valued.reduce((n, p) => n + BigInt(positionValue(p)!), 0n),
  );
  return {
    usd,
    php: toPhp(usd, m.fx),
    unpriced: m.positions.filter((p) => p.unitsMicros > 0 && !p.quote).length,
  };
}
export function quoteAge(q: Quote, now = Date.now()) {
  const age = Math.max(0, Math.floor((now - q.timestamp * 1000) / 60000));
  return `${q.provider === "manual" ? "Manual valuation" : age > 15 ? "Stale / market may be closed" : "Provider quote; feed delay not verified"} · ${age} min old`;
}

export function unitsForAmount(amountUsdMinor: number, priceMicros: number) {
  if (
    !Number.isSafeInteger(amountUsdMinor) ||
    amountUsdMinor <= 0 ||
    !Number.isSafeInteger(priceMicros) ||
    priceMicros <= 0
  )
    throw Error("Enter a positive purchase amount and price.");
  const units =
    (BigInt(amountUsdMinor) * 10_000_000_000n) / BigInt(priceMicros);
  if (units < 1n || units > 1_000_000_000_000n)
    throw Error(
      "Purchase quantity is outside the six-decimal supported range. Use exact broker units instead.",
    );
  return Number(units);
}
export function purchaseTotals(purchases: Purchase[]) {
  const units = purchases.reduce((n, l) => n + BigInt(l.unitsMicros), 0n);
  if (units > 1_000_000_000_000n)
    throw Error("Combined quantity is too large.");
  const amount = purchases.reduce((n, l) => n + BigInt(l.amountUsdMinor), 0n);
  const fees = purchases.reduce((n, l) => n + BigInt(l.feeUsdMinor), 0n);
  return {
    unitsMicros: Number(units),
    amountUsdMinor: checked(amount),
    feesUsdMinor: checked(fees),
    costBasisUsdMinor: checked(amount + fees),
  };
}
export function withPurchases(p: Position, purchases: Purchase[]): Position {
  const totals = purchaseTotals(purchases);
  return positionSchema.parse({
    ...p,
    purchases,
    unitsMicros: totals.unitsMicros,
    costBasisUsdMinor: purchases.length ? totals.costBasisUsdMinor : null,
  });
}
export function makePurchase(input: {
  id: string;
  date: string;
  entryMode: "amount" | "units";
  priceMicros: number;
  amountOrUnits: number;
  feeUsdMinor: number;
}): Purchase {
  const { id, date, entryMode, priceMicros, amountOrUnits, feeUsdMinor } =
    input;
  const unitsMicros =
    entryMode === "amount"
      ? unitsForAmount(amountOrUnits, priceMicros)
      : amountOrUnits;
  const amountUsdMinor =
    entryMode === "amount"
      ? amountOrUnits
      : roundRatio(BigInt(unitsMicros) * BigInt(priceMicros), 10_000_000_000n);
  return purchaseSchema.parse({
    id,
    date,
    entryMode,
    priceMicros,
    unitsMicros,
    amountUsdMinor,
    feeUsdMinor,
  });
}
export function averageCostMicros(p: Position) {
  if (!p.unitsMicros || p.costBasisUsdMinor === null) return null;
  try {
    return roundRatio(
      BigInt(p.costBasisUsdMinor) * 10_000_000_000n,
      BigInt(p.unitsMicros),
    );
  } catch {
    return null;
  }
}
