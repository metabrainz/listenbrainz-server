import * as React from "react";
import { capitalize } from "lodash";
import {
  setThemePreference,
  themePreferences,
  ThemePreference,
  useTheme,
} from "../utils/theme";

function ThemeIcon({ preference }: { preference: ThemePreference }) {
  let icon = "sun";
  if (preference === "system") {
    icon = "system";
  } else if (preference === "dark") {
    icon = "moon";
  }
  return (
    <span
      aria-hidden="true"
      className={`theme-icon-image ${icon}-theme-icon`}
    />
  );
}

export default function ThemeToggle() {
  const [, preference] = useTheme();
  // Only animate the icon after a click, not when the page first loads.
  const [animateIcon, setAnimateIcon] = React.useState(false);
  const next =
    themePreferences[
      (themePreferences.indexOf(preference) + 1) % themePreferences.length
    ];
  const hint = `Click to switch to ${capitalize(next)} mode`;

  return (
    <button
      type="button"
      className="theme-toggle"
      data-theme-toggle
      onClick={() => {
        setAnimateIcon(true);
        setThemePreference(next);
      }}
      aria-label={`Theme: ${capitalize(preference)}. ${hint}`}
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
