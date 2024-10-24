import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

type Section = {
  to: string;
  label: string;
};

const sections: Section[] = [
  { to: "about/", label: "About" },
  { to: "donate/", label: "Donate" },
  { to: "current-status/", label: "Site status" },
  { to: "add-data/", label: "Submitting data" },
  { to: "data/", label: "Using our data" },
  { to: "terms-of-service/", label: "Terms of service" },
];

function AboutLayout() {
  const location = useLocation();
  const activeLabel = sections.find((link) =>
    location.pathname.includes(link.to)
  )?.label;

  return (
    <>
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/about/">About</Link>
          </li>
          {activeLabel && activeLabel !== "About" && (
            <li className="active">{activeLabel}</li>
          )}
        </ol>
      </div>

      <div className="flex flex-wrap" id="settings" role="main">
        <div className="tertiary-nav-vertical">
          ListenBrainz
          <ul>
            {sections.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to}>{link.label}</NavLink>
              </li>
            ))}
            <li>
              <NavLink
                target="_blank"
                rel="noopener noreferrer"
                to="https://listenbrainz.readthedocs.io"
              >
                API docs{" "}
                <FontAwesomeIcon icon={faArrowUpRightFromSquare} size="xs" />
              </NavLink>
            </li>
          </ul>
        </div>
        <div>
          <Outlet />
        </div>
      </div>
    </>
  );
}

export default AboutLayout;
