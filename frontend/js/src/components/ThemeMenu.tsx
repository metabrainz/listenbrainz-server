import * as React from "react";
import { Dropdown } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMoon, faSun } from "@fortawesome/free-regular-svg-icons";
import {
  setThemePreference,
  themePreferences,
  ThemePreference,
  useTheme,
} from "../utils/theme";

/**
 * Monochrome take on the ListenBrainz hexagon (same geometry as the navbar
 * logo): opaque left half, translucent right half, solid outline.
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
        points="15,2.5 26.8,9.3 26.8,20.7 15,27.5"
        fill="currentColor"
        fillOpacity="0.25"
      />
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
  system: "System",
};

function ThemeIcon({ preference }: { preference: ThemePreference }) {
  if (preference === "system") {
    return <SystemThemeIcon />;
  }
  return (
    <FontAwesomeIcon icon={preference === "dark" ? faMoon : faSun} fixedWidth />
  );
}

export default function ThemeMenu() {
  const [, preference] = useTheme();
  const label = `Theme: ${labels[preference]}`;

  return (
    <Dropdown
      className="theme-menu"
      drop="up"
      align="end"
      onSelect={(key) => {
        if (key) {
          setThemePreference(key as ThemePreference);
        }
      }}
    >
      <Dropdown.Toggle
        as="button"
        bsPrefix="theme-toggle"
        type="button"
        data-theme-toggle
        aria-label={label}
        title={label}
      >
        {/* Re-keyed so the swap-in animation replays when the choice changes */}
        <span className="theme-toggle-icon" key={preference}>
          <ThemeIcon preference={preference} />
        </span>
      </Dropdown.Toggle>
      <Dropdown.Menu className="theme-menu-list">
        {themePreferences.map((option) => (
          <Dropdown.Item
            key={option}
            as="button"
            eventKey={option}
            active={option === preference}
            aria-current={option === preference ? "true" : undefined}
          >
            <ThemeIcon preference={option} />
            {labels[option]}
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
}
