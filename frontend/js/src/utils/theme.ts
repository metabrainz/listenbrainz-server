import * as React from "react";

export const themeStorageKey = "listenbrainz-theme";
export const themeChangeEvent = "listenbrainzthemechange";

export type Theme = "light" | "dark";

export function getTheme(): Theme {
  return document.documentElement.dataset.bsTheme === "dark" ? "dark" : "light";
}

export function setTheme(theme: Theme): void {
  document.documentElement.dataset.bsTheme = theme;
  document.documentElement.style.colorScheme = theme;

  try {
    window.localStorage.setItem(themeStorageKey, theme);
  } catch {
    // Private browsing or restrictive browser settings can disable storage.
    // The selected theme still applies for the current page.
  }

  window.dispatchEvent(new Event(themeChangeEvent));
}

export function toggleTheme(): Theme {
  const nextTheme = getTheme() === "dark" ? "light" : "dark";
  setTheme(nextTheme);
  return nextTheme;
}

/** Keep a React surface in sync when the legacy navigation changes the theme. */
export function useTheme(): [Theme, () => void] {
  const [theme, updateTheme] = React.useState<Theme>(getTheme);

  React.useEffect(() => {
    const onThemeChange = () => updateTheme(getTheme());
    window.addEventListener(themeChangeEvent, onThemeChange);
    return () => window.removeEventListener(themeChangeEvent, onThemeChange);
  }, []);

  return [theme, toggleTheme];
}
