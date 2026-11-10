import { getNivoTheme } from "../../src/utils/nivoTheme";
import {
  getTheme,
  setTheme,
  themeChangeEvent,
  themeStorageKey,
  toggleTheme,
} from "../../src/utils/theme";

describe("theme utilities", () => {
  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
  });

  it("updates the document, persists the choice, and notifies subscribers", () => {
    const onThemeChange = jest.fn();
    window.addEventListener(themeChangeEvent, onThemeChange);

    setTheme("dark");

    expect(getTheme()).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(window.localStorage.getItem(themeStorageKey)).toBe("dark");
    expect(onThemeChange).toHaveBeenCalledTimes(1);
    window.removeEventListener(themeChangeEvent, onThemeChange);
  });

  it("toggles between the two supported themes", () => {
    expect(toggleTheme()).toBe("dark");
    expect(toggleTheme()).toBe("light");
  });

  it("uses readable, distinct values for the dark Nivo surfaces", () => {
    const light = getNivoTheme("light");
    const dark = getNivoTheme("dark");

    expect(dark.background).toBe("#1e1e1e");
    expect(dark.textColor).toBe("#e4e4e4");
    expect(dark.grid?.line?.stroke).toBe("#3b3745");
    expect(dark.tooltip?.container?.background).toBe("#252329");
    expect(dark.background).not.toBe(light.background);
  });
});
