/** Institution presets never imply API availability. A future connector must have
 * documented authorized access, explicit consent and independently proven capability. */
export interface AccountConnector {
  id: string;
  capabilities: readonly ("manual" | "csv" | "oauth-sync")[];
  status: "unavailable" | "ready" | "syncing" | "error";
  consent: { grantedAt: string; scopes: string[] } | null;
  lastSuccess: string | null;
  error: string | null;
}
export const manualConnector: AccountConnector = {
  id: "manual",
  capabilities: ["manual", "csv"],
  status: "ready",
  consent: null,
  lastSuccess: null,
  error: null,
};
export const bankSync: AccountConnector = {
  id: "bank-sync",
  capabilities: [],
  status: "unavailable",
  consent: null,
  lastSuccess: null,
  error: "No documented authorized banking integration is configured.",
};
