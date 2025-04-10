import * as React from "react";
import {
  Link,
  NavLink,
  Outlet,
  ScrollRestoration,
  useLocation,
} from "react-router-dom";

type Section = {
  title: string;
  links: { to: string; label: string }[];
};

const sections: Section[] = [
  {
    title: "Music",
    links: [
      { to: "music-services/details/", label: "Connect services" },
      { to: "brainzplayer/", label: "Music player" },
      { to: "import/", label: "Import listens" },
      { to: "link-listens/", label: "Link listens" },
      { to: "../add-data/", label: "Submitting data" },
    ],
  },
  {
    title: "Account",
    links: [
      { to: "./", label: "User settings" },
      { to: "select_timezone/", label: "Timezone" },
      { to: "troi/", label: "Playlist preferences" },
      { to: "export/", label: "Export data" },
      { to: "delete-listens/", label: "Delete listens" },
      { to: "delete/", label: "Delete account" },
    ],
  },
];

function SettingsLayout() {
  const location = useLocation();
  const [activeLabel, setActiveLabel] = React.useState<string>("");

  const getActiveLabel = React.useCallback((path: string) => {
    const newActiveLabel = sections
      .reduce(
        (acc, section) => acc.concat(section.links),
        [] as { to: string; label: string }[]
      )
      .find((link) => path.includes(link.to))?.label;
    return newActiveLabel;
  }, []);

  React.useEffect(() => {
    const newActiveLabel = getActiveLabel(location.pathname);
    setActiveLabel(newActiveLabel || "");
  }, [location.pathname, getActiveLabel]);

  return (
    <>
      <ScrollRestoration />
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/settings/">Settings</Link>
          </li>
          {activeLabel && <li className="active">{activeLabel}</li>}
        </ol>
      </div>

      <div className="flex flex-wrap" id="settings" role="main">
        <div className="tertiary-nav-vertical">
          {sections.map((section) => (
            <React.Fragment key={section.title}>
              <p>{section.title}</p>
              <ul>
                {section.links.map((link) => (
                  <li key={link.to}>
                    <NavLink to={link.to}>{link.label}</NavLink>
                  </li>
                ))}
              </ul>
            </React.Fragment>
          ))}
        </div>
        <div>
          <Outlet />
        </div>
      </div>
    </>
  );
}

export default SettingsLayout;
