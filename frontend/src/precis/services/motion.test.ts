import { afterEach, describe, expect, it, vi } from "vitest";
import { watchMotion } from "./motion";

const motion = () => document.documentElement.getAttribute("data-motion");

describe("watchMotion", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("runs while the page is visible and focused", () => {
    vi.spyOn(document, "hasFocus").mockReturnValue(true);
    const stop = watchMotion();
    expect(motion()).toBe("running");
    stop();
  });

  it("pauses when the window loses focus and resumes on focus", () => {
    const focus = vi.spyOn(document, "hasFocus").mockReturnValue(true);
    const stop = watchMotion();
    focus.mockReturnValue(false);
    window.dispatchEvent(new Event("blur"));
    expect(motion()).toBe("paused");
    focus.mockReturnValue(true);
    window.dispatchEvent(new Event("focus"));
    expect(motion()).toBe("running");
    stop();
  });

  it("pauses while the tab is hidden", () => {
    vi.spyOn(document, "hasFocus").mockReturnValue(true);
    const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    const stop = watchMotion();
    hidden.mockReturnValue(true);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(motion()).toBe("paused");
    stop();
  });

  it("stops listening once stopped", () => {
    const focus = vi.spyOn(document, "hasFocus").mockReturnValue(true);
    watchMotion()();
    focus.mockReturnValue(false);
    window.dispatchEvent(new Event("blur"));
    expect(motion()).toBe("running");
  });
});
