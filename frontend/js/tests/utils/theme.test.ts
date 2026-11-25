import { act, renderHook } from "@testing-library/react";
import { getNivoTheme } from "../../src/utils/nivoTheme";
import {
  getTheme,
  getThemePreference,
  setThemePreference,
  themeChangeEvent,
  themeStorageKey,
  useTheme,
} from "../../src/utils/theme";

// Controllable stand-ins for the OS colour scheme and motion preferences.
const media = {
  dark: false,
  reducedMotion: false,
  listeners: [] as Array<() => void>,
};

function setSystemDark(dark: boolean) {
  media.dark = dark;
  media.listeners.forEach((listener) => listener());
}

describe("theme utilities", () => {
  const originalMatchMedia = window.matchMedia;

  beforeAll(() => {
    window.matchMedia = jest.fn().mockImplementation((query: string) => ({
      get matches() {
        if (query.includes("prefers-color-scheme: dark")) return media.dark;
        if (query.includes("prefers-reduced-motion"))
          return media.reducedMotion;
        return false;
      },
      media: query,
      addEventListener: (_: string, listener: () => void) => {
        if (query.includes("prefers-color-scheme")) {
          media.listeners.push(listener);
        }
      },
      removeEventListener: jest.fn(),
    }));
  });

  afterAll(() => {
    window.matchMedia = originalMatchMedia;
  });

  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
    media.dark = false;
    media.reducedMotion = false;
    delete (document as Partial<Document>).startViewTransition;
  });

  it("defaults to the system preference and ignores unknown stored values", () => {
    expect(getThemePreference()).toBe("system");
    window.localStorage.setItem(themeStorageKey, "sepia");
    expect(getThemePreference()).toBe("system");
  });

  it("applies and persists an explicit choice, and notifies subscribers", () => {
    const onThemeChange = jest.fn();
    window.addEventListener(themeChangeEvent, onThemeChange);

    setThemePreference("dark");

    expect(getTheme()).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(window.localStorage.getItem(themeStorageKey)).toBe("dark");
    expect(onThemeChange).toHaveBeenCalledTimes(1);
    window.removeEventListener(themeChangeEvent, onThemeChange);
  });

  it("stores 'system' separately from the theme it resolves to", () => {
    media.dark = true;
    setThemePreference("system");

    expect(window.localStorage.getItem(themeStorageKey)).toBe("system");
    expect(getTheme()).toBe("dark");
  });

  it("follows OS changes only while 'system' is selected", () => {
    const { result } = renderHook(() => useTheme());
    act(() => setThemePreference("system"));
    expect(result.current).toEqual(["light", "system"]);

    act(() => setSystemDark(true));
    expect(result.current).toEqual(["dark", "system"]);

    act(() => setThemePreference("light"));
    act(() => setSystemDark(false));
    act(() => setSystemDark(true));
    expect(result.current).toEqual(["light", "light"]);
  });

  describe("animated transition", () => {
    let startViewTransition: jest.Mock;

    beforeEach(() => {
      startViewTransition = jest.fn((update: () => void) => {
        update();
        return {
          ready: Promise.resolve(),
          finished: Promise.resolve(),
          updateCallbackDone: Promise.resolve(),
          skipTransition: jest.fn(),
        };
      });
      document.startViewTransition = (startViewTransition as unknown) as Document["startViewTransition"];
      document.documentElement.animate = jest.fn();
    });

    it("reveals the new theme with a circle covering the viewport", async () => {
      setThemePreference("dark");
      await Promise.resolve();

      expect(startViewTransition).toHaveBeenCalledTimes(1);
      expect(getTheme()).toBe("dark");
      const [keyframes, options] = (document.documentElement
        .animate as jest.Mock).mock.calls[0];
      expect(options.pseudoElement).toBe("::view-transition-new(root)");
      const x = window.innerWidth / 2;
      const y = window.innerHeight / 2;
      expect(keyframes.clipPath).toEqual([
        `circle(0px at ${x}px ${y}px)`,
        `circle(${Math.hypot(x, y)}px at ${x}px ${y}px)`,
      ]);
    });

    it("does not animate when the effective theme stays the same", () => {
      setThemePreference("system"); // OS is light, page is light

      expect(startViewTransition).not.toHaveBeenCalled();
      expect(window.localStorage.getItem(themeStorageKey)).toBe("system");
    });

    it("switches instantly when reduced motion is requested", () => {
      media.reducedMotion = true;
      setThemePreference("dark");

      expect(startViewTransition).not.toHaveBeenCalled();
      expect(getTheme()).toBe("dark");
    });
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
