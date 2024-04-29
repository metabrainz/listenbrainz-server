import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

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

function RecommendationsPageLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/");
  const userName = locationArr[3];

  const [activeSection, setActiveSection] = React.useState<string>(
    locationArr[4]
  );

  React.useEffect(() => {
    setActiveSection(locationArr[4]);
  }, [locationArr]);

  return (
    <>
      <div className="secondary-nav dragscroll nochilddrag">
        <ul className="nav nav-tabs" role="tablist">
          <li className="username">
            <div>{userName}</div>
          </li>
          <NavItem
            label="Tracks you might like"
            url={`/recommended/tracks/${userName}/`}
            isActive={activeSection === ""}
          />
          <NavItem
            label="Raw Recommendations"
            url={`/recommended/tracks/${userName}/raw/`}
            isActive={activeSection === "raw"}
          />
        </ul>
      </div>
      <Outlet />
    </>
  );
}

export default RecommendationsPageLayout;
