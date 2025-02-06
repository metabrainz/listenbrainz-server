import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import { FeedModes } from "./types";

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

function UserFeedLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/").filter(Boolean);
  const { currentUser } = React.useContext(GlobalAppContext);

  const loggedIn = currentUser?.name;

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
            url={loggedIn ? "/feed/" : `/login/?next=/feed/`}
            isActive={activeSection === "feed"}
            isDisabled={!loggedIn}
          />
          <NavItem
            label="My Network"
            url={
              loggedIn
                ? `/feed/${FeedModes.Follows}/`
                : `/login/?next=/feed/${FeedModes.Follows}/`
            }
            isActive={
              activeSection === FeedModes.Follows ||
              activeSection === FeedModes.Similar
            }
            isDisabled={!loggedIn}
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
