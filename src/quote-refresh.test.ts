import { expect, it } from "vitest";
import { refreshEligibility, type RefreshContext } from "./quote-refresh";
const ready: RefreshContext = {
  desktop: true,
  sample: false,
  enabled: true,
  hasKey: true,
  positions: 1,
  online: true,
  visible: true,
  autoRefresh: true,
  working: false,
  lastAttempt: 0,
  now: 100000,
};
it("requires explicit provider setup and real desktop workspace before requests", () => {
  for (const override of [
    { desktop: false },
    { sample: true },
    { enabled: false },
    { hasKey: false },
    { positions: 0 },
    { online: false },
    { working: true },
  ])
    expect(refreshEligibility({ ...ready, ...override }).autoReady).toBe(false);
  expect(refreshEligibility(ready).autoReady).toBe(true);
});
it("resumes on reconnect or return to visibility only after the minute cooldown", () => {
  expect(
    refreshEligibility({ ...ready, lastAttempt: ready.now - 59999 }).wait,
  ).toBe(1);
  expect(
    refreshEligibility({ ...ready, lastAttempt: ready.now - 59999 }).autoReady,
  ).toBe(false);
  expect(
    refreshEligibility({ ...ready, lastAttempt: ready.now - 60000 }).autoReady,
  ).toBe(true);
  expect(refreshEligibility({ ...ready, visible: false }).autoReady).toBe(
    false,
  );
  expect(refreshEligibility({ ...ready, visible: false }).manualReady).toBe(
    true,
  );
  expect(refreshEligibility({ ...ready, autoRefresh: false }).autoReady).toBe(
    false,
  );
  expect(refreshEligibility({ ...ready, autoRefresh: false }).manualReady).toBe(
    true,
  );
});
