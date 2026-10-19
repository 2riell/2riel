import { useState } from "react";
import { ExternalLink, ShieldCheck, Upload } from "lucide-react";
import { openResource } from "./Investments";
export const institutions = [
  {
    name: "GCash",
    url: "https://help.gcash.com/hc/en-us/articles/41329110227737-Are-there-other-ways-to-log-in-to-GCash",
    action: "Official app sign-in guidance",
    reason:
      "GCash states that account login is available through its mobile app. SALDO has no approved balance/transaction connection.",
  },
  {
    name: "Maya",
    url: "https://www.maya.ph/",
    action: "Open official Maya website",
    reason:
      "Maya documents partner wallet-linking for payments. That does not grant SALDO permission to read a personal wallet’s balances or history.",
  },
  {
    name: "BPI",
    url: "https://online.bpi.com.ph/",
    action: "Sign in on the official BPI website",
    reason:
      "BPI offers partner APIs. SALDO has no approved partner credentials or verified personal account-information integration.",
  },
  {
    name: "MariBank",
    url: "https://www.maribank.ph/",
    action: "Open official MariBank website",
    reason:
      "MariBank provides mobile banking. No authorized third-party account-read connection has been verified for SALDO.",
  },
  {
    name: "GoTyme",
    url: "https://www.gotyme.com.ph/help/your-account/opening-a-gotyme-bank-account/downloading-the-app",
    action: "Official GoTyme app download guidance",
    reason:
      "GoTyme provides its own banking app. No authorized third-party account-read connection has been verified for SALDO.",
  },
] as const;
export default function Connections({
  onImport,
  canImport,
}: {
  onImport: () => void;
  canImport: boolean;
}) {
  const [error, setError] = useState("");
  return (
    <div>
      <section className="panel investment-intro">
        <ShieldCheck size={30} />
        <div>
          <h2>Bank access stays with your bank.</h2>
          <p>
            These shortcuts open verified official resources in your external
            browser. They do not connect, sync, or share your logged-in session
            with SALDO.
          </p>
          <p>
            SALDO never asks for bank passwords, PINs, account numbers or OTPs.
            Sign in only through your bank’s official app or website.
          </p>
        </div>
      </section>
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <div className="cards">
        {institutions.map((bank) => (
          <section className="panel account-card" key={bank.name}>
            <div className="panel-head">
              <h2>{bank.name}</h2>
              <span className="pill">Sync unavailable</span>
            </div>
            <p>{bank.reason}</p>
            <small>
              Connection: none · Consent: none · Last synchronization: never
            </small>
            <button
              onClick={() =>
                void openResource(bank.name, bank.url).catch((e) =>
                  setError(String(e)),
                )
              }
            >
              <ExternalLink size={14} />
              {bank.action}
            </button>
          </section>
        ))}
      </div>
      <section className="panel investment-intro">
        <div>
          <h2>Bring your statement into SALDO</h2>
          <p>
            Sign in with the official bank, download your statement, convert it
            to SALDO’s universal CSV template, then preview and import. Record a
            verified balance snapshot to reconcile discrepancies. Bank-specific
            statement formats are not yet supported.
          </p>
        </div>
        <button className="primary" disabled={!canImport} onClick={onImport}>
          <Upload size={15} />
          Import statement CSV
        </button>
      </section>
    </div>
  );
}
