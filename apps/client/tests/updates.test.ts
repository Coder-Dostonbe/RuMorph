// Updates outside the app (plain browser, tests): there is nothing to update, so nothing is
// checked and the banner never shows.
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";
import { useUpdates } from "../src/stores/updates";

describe("updates outside the app", () => {
  it("are off and never call the app shell", async () => {
    setActivePinia(createPinia());
    const updates = useUpdates();
    expect(updates.state).toBe("off");
    await updates.check();
    await updates.install();
    expect(updates.state).toBe("off");
    expect(updates.info).toBeNull();
  });
});
