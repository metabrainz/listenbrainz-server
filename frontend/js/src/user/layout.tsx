import * as React from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import GlobalAppContext from "../utils/GlobalAppContext";
import buildAuthUrl from "../utils/auth";

function NavItem({
  label,
  url,
  isActive,
  isDisabled,
}: {
  label: string;
  url: string;
  isActive: boolean;
  isDisabled?: boolean;
}) {
  return (
    <li
      className={`nav-item ${isActive ? "active" : ""} ${
        isDisabled ? "disabled" : ""
      }`}
    >
      <NavLink end className="nav-link" to={url}>
        {label}
      </NavLink>
    </li>
  );
}

function DashboardLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/");
  const { currentUser } = React.useContext(GlobalAppContext);
  const sitewide = locationArr[1] !== "user";
  const userName = sitewide
    ? currentUser?.name
    : decodeURIComponent(locationArr[2]);
  const escapedUserName = encodeURIComponent(userName);

  const [activeSection, setActiveSection] = React.useState<string>(
    sitewide ? locationArr[2] : locationArr[3]
  );

  React.useEffect(() => {
    setActiveSection(locationArr[3]);
  }, [locationArr]);

  return (
    <>
      <div className="secondary-nav dragscroll nochilddrag">
        <ul className="nav nav-tabs" role="tablist">
          <li className="nav-item username">
            {userName ? (
              <Link
                className="nav-link"
                to={userName ? `/user/${escapedUserName}/` : "#"}
              >
                {userName}
              </Link>
            ) : (
              <div>
                <a className="nav-link" href={buildAuthUrl("login")}>
                  Sign in
                </a>
              </div>
            )}
          </li>
          <NavItem
            label="Listens"
            url={userName ? `/user/${escapedUserName}/` : "#"}
            isActive={activeSection === "" && !sitewide}
            isDisabled={!userName}
          />
          <NavItem
            label="Stats"
            url={userName ? `/user/${escapedUserName}/stats/` : "/statistics/"}
            isActive={activeSection === "stats" || sitewide}
          />
          <NavItem
            label="Taste"
            url={userName ? `/user/${escapedUserName}/taste/` : "#"}
            isActive={activeSection === "taste"}
            isDisabled={!userName}
          />
          <NavItem
            label="Playlists"
            url={userName ? `/user/${escapedUserName}/playlists/` : "#"}
            isActive={activeSection === "playlists"}
            isDisabled={!userName}
          />
          <NavItem
            label="Created for you"
            url={userName ? `/user/${escapedUserName}/recommendations/` : "#"}
            isActive={activeSection === "recommendations"}
            isDisabled={!userName}
          />
        </ul>
      </div>
      <div role="main">
        <Outlet />
      </div>
    </>
  );
}

export default DashboardLayout;
