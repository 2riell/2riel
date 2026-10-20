export type RefreshContext = {
  desktop: boolean;
  sample: boolean;
  enabled: boolean;
  hasKey: boolean;
  positions: number;
  online: boolean;
  visible: boolean;
  autoRefresh: boolean;
  working: boolean;
  lastAttempt: number;
  now: number;
};
export function refreshEligibility(c: RefreshContext) {
  const wait =
    c.lastAttempt === 0
      ? 0
      : Math.max(0, Math.ceil((60_000 - (c.now - c.lastAttempt)) / 1000));
  const configured =
    c.desktop && !c.sample && c.enabled && c.hasKey && c.positions > 0;
  const manualReady = configured && c.online && !c.working && wait === 0;
  return {
    wait,
    configured,
    manualReady,
    autoReady: manualReady && c.autoRefresh && c.visible,
  };
}
