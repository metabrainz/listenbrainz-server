import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import GlobalAppContext from "../utils/GlobalAppContext";
import { FeedModes } from "./types";
import buildAuthUrl from "../utils/auth";

function NavItem({
  label,
  url,
  isActive,
  loginRequired,
  loggedIn,
}: {
  label: string;
  url: string;
  isActive: boolean;
  loginRequired?: boolean;
  loggedIn?: boolean;
}) {
  const disable = loginRequired && !loggedIn;
  return (
    <li
      className={`nav-item ${isActive ? "active" : ""} ${
        disable ? "disabled" : ""
      }`}
    >
      {disable ? (
        <a className="nav-link" href={buildAuthUrl("login", url)}>
          {label}
        </a>
      ) : (
        <NavLink end className="nav-link" to={url}>
          {label}
        </NavLink>
      )}
    </li>
  );
}

function UserFeedLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/").filter(Boolean);
  const { currentUser } = React.useContext(GlobalAppContext);

  const loggedIn = Boolean(currentUser?.name);

  const [activeSection, setActiveSection] = React.useState<string>(
    locationArr.at(-1) ?? ""
  );

  React.useEffect(() => {
    setActiveSection(locationArr.at(-1) ?? "");
  }, [locationArr]);

  return (
    <>
      <div className="secondary-nav dragscroll nochilddrag">
        <ul className="nav nav-tabs" role="tablist">
          <NavItem
            label="My Feed"
            url="/feed/"
            isActive={activeSection === "feed"}
            loggedIn={loggedIn}
            loginRequired
          />
          <NavItem
            label="My Network"
            url={`/feed/${FeedModes.Follows}/`}
            isActive={
              activeSection === FeedModes.Follows ||
              activeSection === FeedModes.Similar
            }
            loggedIn={loggedIn}
            loginRequired
          />
          <NavItem
            label="Global"
            url="/recent/"
            isActive={activeSection === "recent"}
          />
        </ul>
      </div>
      <div role="main">
        <Outlet />
      </div>
    </>
  );
}

export default UserFeedLayout;
