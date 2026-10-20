import { describe, it, expect } from "vitest";
import {
  emptyMarket,
  scaled,
  unscale,
  positionValue,
  toPhp,
  quoteAge,
  marketSchema,
  marketTotals,
  type Position,
  makePurchase,
  purchaseTotals,
  withPurchases,
  averageCostMicros,
  positionSchema,
} from "./market";
import { empty, netWorth, validate, type State } from "./engine";
const position = (): Position => ({
  id: "p",
  symbol: "SPY",
  name: "S&P 500 ETF",
  unitsMicros: 500000,
  costBasisUsdMinor: 5000,
  purchases: [],
  quote: {
    symbol: "SPY",
    priceMicros: 123450000,
    previousCloseMicros: 120000000,
    timestamp: 1700000000,
    receivedAt: "2023-11-14T22:13:20.000Z",
    provider: "finnhub",
  },
});
describe("market valuation accuracy and provenance", () => {
  it("parses six-place quantities without multiplying floats", () => {
    expect(scaled("0.123456")).toBe(123456);
    expect(unscale(scaled("100.50"))).toBe("100.5");
    expect(unscale(0)).toBe("0");
    expect(() => scaled("1.1234567")).toThrow();
    expect(() => scaled("-1")).toThrow();
  });
  it("rounds fractional unit valuations to cents once", () => {
    expect(positionValue(position())).toBe(6173);
    const p = position();
    p.unitsMicros = 3000000;
    p.quote!.priceMicros = 290000;
    expect(positionValue(p)).toBe(87);
  });
  it("converts using an explicit fixed-precision dated rate", () => {
    expect(toPhp(1001, { rateMicros: 56123456, date: "2026-01-01" })).toBe(
      56180,
    );
    expect(toPhp(1001, null)).toBeNull();
  });
  it("does not invent prices or value unpriced holdings at cost", () => {
    const m = emptyMarket();
    m.positions = [{ ...position(), quote: null }];
    expect(marketTotals(m)).toEqual({ usd: 0, php: null, unpriced: 1 });
    expect(positionValue(m.positions[0])).toBeNull();
  });
  it("labels stale prices by market time rather than download time", () => {
    const q = position().quote!;
    q.receivedAt = new Date(1700100000000).toISOString();
    expect(quoteAge(q, 1700100000000)).toContain("Stale");
    q.provider = "manual";
    expect(quoteAge(q)).toContain("Manual");
  });
  it("rejects duplicate symbols and mismatched quote tickers", () => {
    const m = emptyMarket();
    m.positions = [position(), { ...position(), id: "q" }];
    expect(() => marketSchema.parse(m)).toThrow();
    m.positions = [{ ...position(), symbol: "VOD.L", quote: null }];
    expect(() => marketSchema.parse(m)).toThrow();
    m.positions = [position()];
    m.positions[0].quote!.symbol = "VOO";
    expect(() => marketSchema.parse(m)).toThrow();
  });
  it("informational positions never create ledger assets or cash movements", () => {
    const s = empty();
    const before = netWorth(s);
    s.market.positions = [position()];
    expect(netWorth(validate(s))).toBe(before);
    expect(s.entries).toEqual([]);
  });
  it("loads existing v0.1 state with a disabled empty market", () => {
    const s: Partial<State> = empty();
    delete s.market;
    expect(validate(s as State).market).toEqual(emptyMarket());
  });
  it("rejects negative basis, invalid dates and excess watchlist sizes", () => {
    const m = emptyMarket();
    m.positions = [{ ...position(), costBasisUsdMinor: -1 }];
    expect(() => marketSchema.parse(m)).toThrow();
    m.positions = [];
    m.fx = { rateMicros: 56000000, date: "2026-02-30" };
    expect(() => marketSchema.parse(m)).toThrow();
    m.fx = null;
    m.positions = Array.from({ length: 11 }, (_, i) => ({
      ...position(),
      id: String(i),
      symbol: "A" + i,
    }));
    expect(() => marketSchema.parse(m)).toThrow();
  });
});

describe("purchase amounts, multiple entry prices and average cost", () => {
  const buy = (id: string, amount: number, price: string, fee = 0) =>
    makePurchase({
      id,
      date: "2026-01-01",
      entryMode: "amount",
      priceMicros: scaled(price),
      amountOrUnits: amount,
      feeUsdMinor: fee,
    });
  it("combines multiple buy prices and fees into exact units, basis and average cost", () => {
    const lots = [
      buy("one", 100000, "500", 100),
      buy("two", 110000, "550", 100),
    ];
    expect(purchaseTotals(lots)).toEqual({
      unitsMicros: 4000000,
      amountUsdMinor: 210000,
      feesUsdMinor: 200,
      costBasisUsdMinor: 210200,
    });
    const p = withPurchases(position(), lots);
    expect(averageCostMicros(p)).toBe(525500000);
    expect(
      averageCostMicros({
        ...p,
        unitsMicros: 1,
        costBasisUsdMinor: 9_000_000_000_000_000,
      }),
    ).toBeNull();
    p.quote!.priceMicros = 600000000;
    expect(positionValue(p)! - p.costBasisUsdMinor!).toBe(29800);
    const s = empty();
    s.market.positions = [p];
    expect(netWorth(validate(s))).toBe(0);
    expect(s.entries).toHaveLength(0);
  });
  it("cash-based fractional units never round above the amount and broker units round cash once", () => {
    const lot = buy("fraction", 10000, "333.33");
    expect(lot.unitsMicros).toBe(300003);
    expect(
      BigInt(lot.unitsMicros) * BigInt(lot.priceMicros),
    ).toBeLessThanOrEqual(BigInt(lot.amountUsdMinor) * 10_000_000_000n);
    const broker = makePurchase({
      id: "broker",
      date: "2026-01-01",
      entryMode: "units",
      priceMicros: scaled("123.45"),
      amountOrUnits: 500000,
      feeUsdMinor: 0,
    });
    expect(broker.amountUsdMinor).toBe(6173);
  });
  it("rejects invalid dates, zero amounts, duplicate purchases and tampered totals", () => {
    expect(() => buy("zero", 0, "500")).toThrow();
    const p = withPurchases(position(), [buy("one", 100000, "500")]);
    expect(positionSchema.safeParse({ ...p, unitsMicros: 1 }).success).toBe(
      false,
    );
    expect(() => withPurchases(p, [p.purchases[0], p.purchases[0]])).toThrow();
    expect(
      positionSchema.safeParse({
        ...p,
        purchases: [{ ...p.purchases[0], date: "2026-02-30" }],
      }).success,
    ).toBe(false);
    expect(
      positionSchema.safeParse({
        ...p,
        purchases: [{ ...p.purchases[0], date: "2999-01-01" }],
      }).success,
    ).toBe(false);
    expect(
      positionSchema.safeParse({
        ...p,
        purchases: [{ ...p.purchases[0], priceMicros: 1 }],
      }).success,
    ).toBe(false);
  });
  it("loads prior manual positions and removing the final purchase clears tracked totals", () => {
    const old: Partial<Position> = position();
    delete old.purchases;
    expect(positionSchema.parse(old).purchases).toEqual([]);
    const p = withPurchases(position(), [buy("one", 100000, "500")]);
    expect(withPurchases(p, [])).toMatchObject({
      unitsMicros: 0,
      costBasisUsdMinor: null,
      purchases: [],
    });
  });
});
