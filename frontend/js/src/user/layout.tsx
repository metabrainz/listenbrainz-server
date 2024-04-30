import * as React from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";

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
      className={`${isActive ? "active" : ""} ${isDisabled ? "disabled" : ""}`}
    >
      <NavLink to={url}>{label}</NavLink>
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
          <li className="username">
            {userName ? (
              <Link to={userName ? `/user/${userName}/` : "#"}>{userName}</Link>
            ) : (
              <div>
                <Link to="/login/">Sign in</Link>
              </div>
            )}
          </li>
          <NavItem
            label="Listens"
            url={userName ? `/user/${userName}/` : "#"}
            isActive={activeSection === "" && !sitewide}
            isDisabled={!userName}
          />
          <NavItem
            label="Stats"
            url={userName ? `/user/${userName}/stats/` : "/statistics/"}
            isActive={activeSection === "stats" || sitewide}
          />
          <NavItem
            label="Taste"
            url={userName ? `/user/${userName}/taste/` : "#"}
            isActive={activeSection === "taste"}
            isDisabled={!userName}
          />
          <NavItem
            label="Playlists"
            url={userName ? `/user/${userName}/playlists/` : "#"}
            isActive={activeSection === "playlists"}
            isDisabled={!userName}
          />
          <NavItem
            label="Created for you"
            url={userName ? `/user/${userName}/recommendations/` : "#"}
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
