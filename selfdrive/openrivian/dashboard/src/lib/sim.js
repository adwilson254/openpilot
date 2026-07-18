// Simulator REMOVED for production (dev). It exists only on feature branches / dev-test.
// These permanently-disabled stubs keep the bundle building; there is no simulator and
// no recorded-drive data in this build.
export function simEnabled() { return false; }
export function simSnapshot() { return {}; }
export async function loadSimTimeline() { return { hz: 5, topics: [], frames: [] }; }
