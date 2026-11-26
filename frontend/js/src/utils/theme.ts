import * as React from "react";
import { flushSync } from "react-dom";

export const themeStorageKey = "listenbrainz-theme";
export const themeChangeEvent = "listenbrainzthemechange";

/** The colours actually painted on the page. */
export type Theme = "light" | "dark";
/** What the user picked. "system" follows the OS `prefers-color-scheme`. */
export type ThemePreference = Theme | "system";

export const themePreferences: ThemePreference[] = ["light", "dark", "system"];

const darkSchemeQuery = "(prefers-color-scheme: dark)";
const reducedMotionQuery = "(prefers-reduced-motion: reduce)";
// Class on <html> that scopes the reveal CSS to theme changes only, so any
// other view transition keeps the browser's default cross-fade.
const transitionClass = "lb-theme-transition";

function isThemePreference(value: unknown): value is ThemePreference {
  return themePreferences.includes(value as ThemePreference);
}

export function getThemePreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(themeStorageKey);
    // New visitors start on Light so the familiar sun/moon icons come first.
    return isThemePreference(stored) ? stored : "light";
  } catch {
    return "light";
  }
}

export function getSystemTheme(): Theme {
  return window.matchMedia?.(darkSchemeQuery).matches ? "dark" : "light";
}

export function resolveTheme(preference: ThemePreference): Theme {
  return preference === "system" ? getSystemTheme() : preference;
}

/** The theme currently applied to the document. */
export function getTheme(): Theme {
  return document.documentElement.dataset.bsTheme === "dark" ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.bsTheme = theme;
  document.documentElement.style.colorScheme = theme;
}

function notifyThemeChange(): void {
  // Flush React updates synchronously so the view transition snapshots the
  // fully re-rendered page (icons, Nivo charts…) rather than a stale one.
  flushSync(() => {
    window.dispatchEvent(new Event(themeChangeEvent));
  });
}

/** Centre of the visible navbar theme button, the origin of the reveal. */
function getRevealOrigin(): { x: number; y: number } {
  const visibleRect = Array.from(
    document.querySelectorAll<HTMLElement>("[data-theme-toggle]")
  )
    .map((toggle) => toggle.getBoundingClientRect())
    .find(
      (rect) =>
        rect.width > 0 &&
        rect.height > 0 &&
        rect.right > 0 &&
        rect.bottom > 0 &&
        rect.left < window.innerWidth &&
        rect.top < window.innerHeight
    );
  if (visibleRect) {
    return {
      x: visibleRect.left + visibleRect.width / 2,
      y: visibleRect.top + visibleRect.height / 2,
    };
  }
  // e.g. collapsed mobile navigation: reveal from the middle of the screen.
  return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
}

function canAnimate(): boolean {
  return (
    typeof document.startViewTransition === "function" &&
    document.visibilityState === "visible" &&
    !window.matchMedia?.(reducedMotionQuery).matches
  );
}

// Theme the document is heading to, including one still being revealed, so
// rapid changes compare against the right state.
let targetTheme: Theme | undefined;

function transitionTo(theme: Theme): void {
  if (theme === (targetTheme ?? getTheme())) {
    // Effective theme is unchanged (e.g. Dark -> System on a dark OS):
    // nothing to animate, but subscribers still need the new preference.
    notifyThemeChange();
    return;
  }

  if (!canAnimate()) {
    applyTheme(theme);
    notifyThemeChange();
    return;
  }

  const { x, y } = getRevealOrigin();
  // Distance to the farthest viewport corner, so the circle covers it all.
  const radius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  );

  const root = document.documentElement;
  // Set the initial mask before the browser creates the transition
  // pseudo-elements. Without this, a complex page can briefly paint the new
  // snapshot at full size before the Web Animation starts.
  root.style.setProperty("--lb-theme-transition-x", `${x}px`);
  root.style.setProperty("--lb-theme-transition-y", `${y}px`);
  root.style.setProperty("--lb-theme-transition-radius", `${radius}px`);
  root.classList.add(transitionClass);
  targetTheme = theme;

  const transition = document.startViewTransition(() => {
    applyTheme(theme);
    notifyThemeChange();
  });

  transition.finished.finally(() => {
    if (targetTheme === theme) {
      targetTheme = undefined;
      root.classList.remove(transitionClass);
      root.style.removeProperty("--lb-theme-transition-x");
      root.style.removeProperty("--lb-theme-transition-y");
      root.style.removeProperty("--lb-theme-transition-radius");
    }
  });
}

export function setThemePreference(preference: ThemePreference): void {
  try {
    window.localStorage.setItem(themeStorageKey, preference);
  } catch {
    // Private browsing or restrictive browser settings can disable storage.
    // The selected theme still applies for the current page.
  }
  transitionTo(resolveTheme(preference));
}

let followingSystem = false;

/** Re-resolve the theme when the OS scheme changes while "system" is picked. */
function followSystemTheme(): void {
  if (followingSystem || !window.matchMedia) {
    return;
  }
  followingSystem = true;
  window.matchMedia(darkSchemeQuery).addEventListener("change", () => {
    if (getThemePreference() === "system") {
      transitionTo(getSystemTheme());
    }
  });
}

/**
 * Current applied theme and stored preference, kept in sync with changes
 * made from the navigation (React or legacy) or by the operating system.
 */
export function useTheme(): [Theme, ThemePreference] {
  const [state, setState] = React.useState<[Theme, ThemePreference]>(() => [
    getTheme(),
    getThemePreference(),
  ]);

  React.useEffect(() => {
    followSystemTheme();
    const onThemeChange = () => {
      const theme = getTheme();
      const preference = getThemePreference();
      setState((prev) =>
        prev[0] === theme && prev[1] === preference ? prev : [theme, preference]
      );
    };
    // Catch up on anything that changed between first render and now.
    onThemeChange();
    window.addEventListener(themeChangeEvent, onThemeChange);
    return () => window.removeEventListener(themeChangeEvent, onThemeChange);
  }, []);

  return state;
}
