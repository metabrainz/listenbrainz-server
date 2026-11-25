import * as React from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";
import {
  setThemePreference,
  themePreferences,
  ThemePreference,
  useTheme,
} from "../utils/theme";

/**
 * Monochrome take on the ListenBrainz hexagon (same geometry as the navbar
 * logo): opaque left half, transparent right half, solid outline.
 */
export function SystemThemeIcon() {
  return (
    <svg
      className="system-theme-icon"
      viewBox="0 0 30 30"
      width="1em"
      height="1em"
      aria-hidden="true"
      focusable="false"
    >
      <polygon points="15,2.5 3.2,9.3 3.2,20.7 15,27.5" fill="currentColor" />
      <polygon
        points="15,1.5 27.7,8.8 27.7,21.2 15,28.5 2.3,21.2 2.3,8.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const labels: Record<ThemePreference, string> = {
  light: "Light",
  dark: "Dark",
  system: "Auto",
};

// Outline sun and moon drawn to match the stroke weight of the hexagon icon.
// (Font Awesome's regular sun reads as a gear at navbar size.)
const outlineProps = {
  // Cropped to the drawn shape so the icons fill the same box as the hexagon.
  viewBox: "1.5 1.5 21 21",
  width: "1em",
  height: "1em",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

export function SunIcon() {
  return (
    <svg className="sun-theme-icon" {...outlineProps}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
    </svg>
  );
}

export function MoonIcon() {
  return (
    <svg className="moon-theme-icon" {...outlineProps}>
      <path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a6.8 6.8 0 0 0 10.7 10.7Z" />
    </svg>
  );
}

function ThemeIcon({ preference }: { preference: ThemePreference }) {
  if (preference === "system") {
    return <SystemThemeIcon />;
  }
  return preference === "dark" ? <MoonIcon /> : <SunIcon />;
}

const wittyLinesLight = [
  "Same listens, more photons.",
  "Good for reading track listings in a sunny room.",
  "Back to the original ListenBrainz look.",
  "If you were in a dark room, sorry about your eyes.",
  "Easy to read in daylight, rough at 3 a.m.",
  "White background, purple links, same old ListenBrainz.",
  "Daytime listening, daytime colours.",
  "Squint responsibly.",
  "Rise and shine.",
  "Let there be light.",
];

const wittyLinesDark = [
  "Easier on the eyes for late-night scrobbling.",
  "OLED screens say thanks.",
  "Cover art stands out more on a dark background.",
  "No more squinting at the feed.",
  "For listening with the lights off.",
  "Kinder to your eyes at 2 a.m.",
  "The screen's a bit quieter now.",
  "Fewer photons at bedtime.",
  "The brightness has been turned down for you.",
  "You're welcome.",
];

const wittyLinesAuto = [
  "We'll match whatever your OS is doing.",
  "Your system decides now. We follow.",
  "If your system switches at sunset, so do we.",
  "Monkey see, monkey do.",
  "Light by day, dark by night.",
  "Change your system theme and we'll copy it.",
  "The OS is in charge of the lights now.",
  "Same theme as the rest of your screen.",
  "Set it once, then forget this button exists.",
  "Copying your system's homework.",
];

const wittyLines: Record<ThemePreference, string[]> = {
  light: wittyLinesLight,
  dark: wittyLinesDark,
  system: wittyLinesAuto,
};

function randomWittyLine(preference: ThemePreference): string {
  const lines = wittyLines[preference];
  return lines[Math.floor(Math.random() * lines.length)];
}

const themeToastId = "theme-change";

/** One toast for theme changes: rapid clicks update it instead of stacking. */
function announceTheme(preference: ThemePreference) {
  const content = (
    <ToastMsg
      title={`${labels[preference]} mode`}
      message={randomWittyLine(preference)}
    />
  );
  const options = {
    icon: <ThemeIcon preference={preference} />,
    autoClose: 3000,
  };
  if (toast.isActive(themeToastId)) {
    toast.update(themeToastId, { render: content, ...options });
  } else {
    toast(content, { toastId: themeToastId, ...options });
  }
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
        announceTheme(next);
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
