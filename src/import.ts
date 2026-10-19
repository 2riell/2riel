import Papa from "papaparse";
import { id, minor, type Entry, type State } from "./engine";
export function previewCSV(text: string, account: string, s: State): Entry[] {
  if (text.length > 2_000_000) throw Error("CSV exceeds 2 MB");
  const result = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
  });
  if (result.errors.length) throw Error(result.errors[0].message);
  for (const col of ["date", "description", "kind", "amount", "category"])
    if (!result.meta.fields?.includes(col))
      throw Error(`Missing column: ${col}`);
  return result.data
    .map((r, i) => {
      if (!["income", "expense", "refund"].includes(r.kind))
        throw Error(
          `Row ${i + 2}: supported types are income, expense, refund`,
        );
      const amount = minor(r.amount);
      const key = JSON.stringify([
        account,
        r.date,
        r.description,
        r.kind,
        amount,
        r.category,
      ]);
      return {
        id: id(),
        date: r.date,
        description: r.description,
        kind: r.kind as Entry["kind"],
        account,
        amount,
        fee: 0,
        category: r.category,
        source: "csv" as const,
        importKey: key,
      };
    })
    .filter((e) => !s.entries.some((x) => x.importKey === e.importKey));
}
export function csvExport(s: State) {
  return Papa.unparse(
    s.entries.map((e) => ({
      ...e,
      amount: (e.amount / 100).toFixed(2),
      fee: (e.fee / 100).toFixed(2),
    })),
    { escapeFormulae: true },
  );
}
