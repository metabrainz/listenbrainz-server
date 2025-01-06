import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router";
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
      <NavLink to={url} viewTransition>
        {label}
      </NavLink>
    </li>
  );
}

function UserFeedLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/");
  const { currentUser } = React.useContext(GlobalAppContext);

  const loggedIn = currentUser?.name;

  const [activeSection, setActiveSection] = React.useState<string>(
    locationArr[1]
  );

  React.useEffect(() => {
    setActiveSection(locationArr[1]);
  }, [locationArr]);

  return (
    <>
      <div className="secondary-nav dragscroll nochilddrag">
        <ul className="nav nav-tabs" role="tablist">
          <NavItem
            label="My Feed"
            url={loggedIn ? "/feed/" : "#"}
            isActive={activeSection === "feed"}
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
