import { useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import { id, minor, today } from "./engine";
import {
  makePurchase,
  purchaseTotals,
  scaled,
  unscale,
  type Position,
  type Purchase,
} from "./market";
type Props = {
  position: Position;
  hidden: boolean;
  onClose: () => void;
  onSave: (purchases: Purchase[]) => Promise<boolean>;
};
const blank = () => ({
  date: today(),
  price: "",
  quantity: "",
  fee: "0",
  mode: "amount" as "amount" | "units",
});
export default function PurchaseHistory({
  position,
  hidden,
  onClose,
  onSave,
}: Props) {
  const [values, setValues] = useState(blank),
    [editing, setEditing] = useState<string | null>(null),
    [replace, setReplace] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const display = (n: number) =>
    hidden
      ? "USD ••••••"
      : new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
        }).format(n / 100);
  const unitPrice = (n: number) => (hidden ? "USD ••••••" : `$${unscale(n)}`);
  function draft(purchaseId: string) {
    return makePurchase({
      id: purchaseId,
      date: values.date,
      entryMode: values.mode,
      priceMicros: scaled(values.price),
      amountOrUnits:
        values.mode === "amount"
          ? minor(values.quantity)
          : scaled(values.quantity),
      feeUsdMinor: minor(values.fee || "0"),
    });
  }
  let preview: Purchase | null = null;
  try {
    preview = draft(editing || "preview");
  } catch {
    /* Incomplete inputs have no estimate. */
  }
  const totals = purchaseTotals(position.purchases);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!position.purchases.length && position.unitsMicros > 0 && !replace) {
      setError(
        "Confirm replacing the manual totals before starting a purchase history.",
      );
      return;
    }
    setBusy(true);
    try {
      const purchase = draft(editing || id());
      const purchases = editing
        ? position.purchases.map((p) => (p.id === editing ? purchase : p))
        : [...position.purchases, purchase];
      if (await onSave(purchases)) {
        setValues(blank());
        setEditing(null);
        setReplace(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check the purchase details.");
    } finally {
      setBusy(false);
    }
  }
  async function remove(p: Purchase) {
    if (
      !confirm(
        "Remove this purchase record and recalculate tracked units/cost? This correction does not record a sale or change ledger cash.",
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      if (
        (await onSave(position.purchases.filter((x) => x.id !== p.id))) &&
        editing === p.id
      ) {
        setEditing(null);
        setValues(blank());
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not save purchase records.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      id="purchase-history"
      className="panel purchase-history"
      aria-label={`${position.symbol} purchase history`}
    >
      <div className="panel-head">
        <div>
          <span className="eyebrow">YOUR PURCHASE RECORDS</span>
          <h2>{position.symbol} · Purchase history</h2>
          <p>
            Record the amount invested and price for each buy, or enter the
            exact units from your broker.
          </p>
        </div>
        <button
          className="icon"
          aria-label="Close purchase history"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="purchase-summary">
        <div>
          <small>Invested before fees</small>
          <strong>{display(totals.amountUsdMinor)}</strong>
        </div>
        <div>
          <small>Purchase fees</small>
          <strong>{display(totals.feesUsdMinor)}</strong>
        </div>
        <div>
          <small>Recorded units</small>
          <strong>{hidden ? "•••" : unscale(totals.unitsMicros)}</strong>
        </div>
      </div>
      <div className="purchase-layout">
        <form onSubmit={(e) => void submit(e)} className="purchase-form">
          <h2>{editing ? "Edit purchase" : "Record a buy"}</h2>
          <label>
            Purchase date
            <input
              aria-label="Purchase date"
              type="date"
              value={values.date}
              max={today()}
              required
              onChange={(e) => setValues({ ...values, date: e.target.value })}
            />
          </label>
          <label>
            Purchase price per unit (USD)
            <input
              aria-label="Purchase price per unit (USD)"
              type={hidden ? "password" : "text"}
              inputMode="decimal"
              placeholder="For example, 500.25"
              value={values.price}
              required
              onChange={(e) => setValues({ ...values, price: e.target.value })}
            />
          </label>
          <label>
            Entry method
            <select
              aria-label="Purchase entry method"
              value={values.mode}
              onChange={(e) =>
                setValues({
                  ...values,
                  mode: e.target.value as "amount" | "units",
                  quantity: "",
                })
              }
            >
              <option value="amount">Amount invested → estimated units</option>
              <option value="units">
                Exact broker units → purchase amount
              </option>
            </select>
          </label>
          <label>
            {values.mode === "amount"
              ? "Amount invested before fees (USD)"
              : "Exact units purchased"}
            <input
              aria-label={
                values.mode === "amount"
                  ? "Amount invested before fees (USD)"
                  : "Exact units purchased"
              }
              type={hidden ? "password" : "text"}
              inputMode="decimal"
              required
              value={values.quantity}
              placeholder={
                values.mode === "amount"
                  ? "For example, 1000.00"
                  : "Up to 6 decimals"
              }
              onChange={(e) =>
                setValues({ ...values, quantity: e.target.value })
              }
            />
          </label>
          <label>
            Purchase fees (USD)
            <input
              aria-label="Purchase fees (USD)"
              type={hidden ? "password" : "text"}
              inputMode="decimal"
              value={values.fee}
              onChange={(e) => setValues({ ...values, fee: e.target.value })}
            />
          </label>
          {preview && (
            <div className="purchase-preview" role="status">
              <strong>
                {hidden ? "•••" : unscale(preview.unitsMicros)}{" "}
                {values.mode === "amount" ? "estimated units" : "units"}
              </strong>
              <small>
                {display(preview.amountUsdMinor + preview.feeUsdMinor)} total
                cost including fees
              </small>
            </div>
          )}
          {!position.purchases.length && position.unitsMicros > 0 && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={replace}
                onChange={(e) => setReplace(e.target.checked)}
              />{" "}
              Replace existing manual units and cost with these purchase
              records. Include every existing buy to preserve the full position.
            </label>
          )}
          <div className="row-actions">
            <button
              className="primary"
              disabled={busy || (!editing && position.purchases.length >= 200)}
            >
              <Plus size={15} />
              {editing ? "Save purchase changes" : "Save purchase"}
            </button>
            {editing && (
              <button
                type="button"
                onClick={() => {
                  setEditing(null);
                  setValues(blank());
                  setError("");
                }}
              >
                Cancel edit
              </button>
            )}
          </div>
          <small>
            USD amounts; fees are separate. Cash-based units are rounded down to
            6 decimals and are estimates. Use exact broker units where
            available. These records do not connect to a broker or debit your
            accounts.
          </small>
        </form>
        <div className="purchase-records">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date / entry</th>
                  <th className="right">Buy price</th>
                  <th className="right">Units</th>
                  <th className="right">Amount / fee</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {[...position.purchases]
                  .sort((a, b) => b.date.localeCompare(a.date))
                  .map((p) => (
                    <tr key={p.id}>
                      <td>
                        {p.date}
                        <small>
                          {p.entryMode === "amount"
                            ? "Estimated units"
                            : "Broker units"}
                        </small>
                      </td>
                      <td className="right mono">{unitPrice(p.priceMicros)}</td>
                      <td className="right mono">
                        {hidden ? "•••" : unscale(p.unitsMicros)}
                      </td>
                      <td className="right mono">
                        {display(p.amountUsdMinor)}
                        <small>{display(p.feeUsdMinor)} fee</small>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="text"
                            disabled={busy}
                            aria-label={`Edit purchase ${p.id}`}
                            onClick={() => {
                              setEditing(p.id);
                              setError("");
                              setValues({
                                date: p.date,
                                price: unscale(p.priceMicros),
                                quantity:
                                  p.entryMode === "amount"
                                    ? (p.amountUsdMinor / 100).toFixed(2)
                                    : unscale(p.unitsMicros),
                                fee: (p.feeUsdMinor / 100).toFixed(2),
                                mode: p.entryMode,
                              });
                            }}
                          >
                            Edit
                          </button>
                          <button
                            className="text danger"
                            disabled={busy}
                            aria-label={`Remove purchase ${p.id}`}
                            onClick={() => void remove(p)}
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {!position.purchases.length && (
              <div className="empty">
                No purchase records yet. Add each buy to calculate your invested
                amount and average cost.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
