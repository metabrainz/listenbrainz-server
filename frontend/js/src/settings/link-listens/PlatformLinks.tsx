import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronCircleRight,
  faExternalLinkAlt,
  faSearch,
} from "@fortawesome/free-solid-svg-icons";
import ListenControl from "../../common/listens/ListenControl";
import { MissingDataLink } from "./utils";

type BootstrapWindow = Window & {
  bootstrap?: {
    Dropdown: {
      getInstance: (toggle: Element) => { update: () => void } | null;
    };
  };
};

function actionText(link: MissingDataLink): string {
  switch (link.kind) {
    case "source":
      return link.label;
    case "album":
      return "Open album";
    case "harmony":
      return "Look up album in\nHarmony";
    case "sambl":
      return "Look up album in SAMBL";
    default:
      return link.label.endsWith("for album")
        ? "Search for album"
        : "Search for track";
  }
}

export default function PlatformLinks({ links }: { links: MissingDataLink[] }) {
  const container = React.useRef<HTMLLIElement>(null);
  const groups = new Map<string, MissingDataLink[]>();
  links.forEach((link) => {
    const group = groups.get(link.service) ?? [];
    group.push(link);
    groups.set(link.service, group);
  });
  const hasLinks = links.length > 0;

  React.useEffect(() => {
    const element = container.current;
    const toggle = element
      ?.closest(".listen-card")
      ?.querySelector('[data-bs-toggle="dropdown"]');
    if (!element || !toggle) return undefined;
    const reset = () => {
      element.querySelectorAll("details").forEach((details) => {
        details.removeAttribute("open");
      });
    };
    toggle.addEventListener("hidden.bs.dropdown", reset);
    return () => toggle.removeEventListener("hidden.bs.dropdown", reset);
  }, [hasLinks]);

  const updatePosition = () => {
    const toggle = container.current
      ?.closest(".listen-card")
      ?.querySelector('[data-bs-toggle="dropdown"]');
    if (toggle)
      (window as BootstrapWindow).bootstrap?.Dropdown.getInstance(
        toggle
      )?.update();
  };

  if (!hasLinks) return null;
  return (
    <li className="link-listens-service-links" ref={container}>
      {Array.from(groups, ([service, items]) => (
        <details key={service} onToggle={updatePosition}>
          <summary
            className="dropdown-item"
            onClick={(event) => event.stopPropagation()}
          >
            <FontAwesomeIcon
              icon={faChevronCircleRight}
              fixedWidth
              className="summary-indicator"
            />
            {service}
          </summary>
          <ul>
            {items.map((item) => (
              <li
                key={item.key}
                className={item.kind === "harmony" ? "harmony-link" : undefined}
              >
                <ListenControl
                  text={actionText(item)}
                  title={item.label}
                  ariaLabel={item.label}
                  link={item.href}
                  icon={item.kind === "search" ? faSearch : faExternalLinkAlt}
                  anchorTagAttributes={{
                    target: "_blank",
                    rel: "noopener noreferrer",
                  }}
                />
              </li>
            ))}
          </ul>
        </details>
      ))}
    </li>
  );
}
