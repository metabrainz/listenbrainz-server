import * as React from "react";
import {
  setThemePreference,
  themePreferences,
  ThemePreference,
  useTheme,
} from "../utils/theme";

const labels: Record<ThemePreference, string> = {
  light: "Light",
  dark: "Dark",
  system: "Auto",
};

// Outline icons, drawn so the three modes look like a set. (Font Awesome's
// regular sun reads as a gear at navbar size.)
const outlineProps = {
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

/**
 * Each icon's viewBox is cropped to its own shape (stroke included). The solid
 * moon reads larger than the sparse sun and sun-moon, so those two are drawn
 * bigger, with a thinner stroke so lines look equally thick on screen.
 */
const largeIconProps = { width: "1.2em", height: "1.2em", strokeWidth: 1.3 };
const moonIconProps = { width: "0.93em", height: "0.93em", strokeWidth: 1.6 };

export function SunIcon() {
  return (
    <svg
      className="sun-theme-icon"
      {...outlineProps}
      {...largeIconProps}
      viewBox="1.7 1.7 20.6 20.6"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
    </svg>
  );
}

// Lucide's moon (ISC licence): the same rounded moon as in the Auto icon.
export function MoonIcon() {
  return (
    <svg
      className="moon-theme-icon"
      {...outlineProps}
      {...moonIconProps}
      viewBox="2.2 2.2 19.6 19.6"
    >
      <path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401" />
    </svg>
  );
}

// Sun-moon from Lucide (ISC licence).
export function SystemThemeIcon() {
  return (
    <svg
      className="system-theme-icon"
      {...outlineProps}
      {...largeIconProps}
      viewBox="2.2 1.2 20.6 20.6"
    >
      <path d="M12 2v2" />
      <path d="M14.837 16.385a6 6 0 1 1-7.223-7.222c.624-.147.97.66.715 1.248a4 4 0 0 0 5.26 5.259c.589-.255 1.396.09 1.248.715" />
      <path d="M16 12a4 4 0 0 0-4-4" />
      <path d="m19 5-1.256 1.256" />
      <path d="M20 12h2" />
    </svg>
  );
}

function ThemeIcon({ preference }: { preference: ThemePreference }) {
  if (preference === "system") {
    return <SystemThemeIcon />;
  }
  return preference === "dark" ? <MoonIcon /> : <SunIcon />;
}

export default function ThemeToggle() {
  const [, preference] = useTheme();
  // Only animate the icon after a click, not when the page first loads.
  const [animateIcon, setAnimateIcon] = React.useState(false);
  const next =
    themePreferences[
      (themePreferences.indexOf(preference) + 1) % themePreferences.length
    ];
  const hint = `Click to switch to ${labels[next]} mode`;

  return (
    <button
      type="button"
      className="theme-toggle"
      data-theme-toggle
      onClick={() => {
        setAnimateIcon(true);
        setThemePreference(next);
      }}
      aria-label={`Theme: ${labels[preference]}. ${hint}`}
      title={hint}
    >
      {/* Re-keyed so the swap-in animation replays when the choice changes */}
      <span
        className={`theme-toggle-icon${animateIcon ? " animate" : ""}`}
        key={preference}
      >
        <ThemeIcon preference={preference} />
      </span>
    </button>
  );
}
