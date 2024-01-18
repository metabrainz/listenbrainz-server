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

function UserFeedLayout() {
  const location = useLocation();
  const locationArr = location?.pathname?.split("/");
  const [activeSection, setActiveSection] = React.useState<string>(
    locationArr[3]
  );
  const user = {
    musicbrainz_id: locationArr[2],
  };

  React.useEffect(() => {
    setActiveSection(locationArr[3]);
  }, [locationArr]);

  return (
    <>
      <div className="secondary-nav dragscroll nochilddrag">
        <ul className="nav nav-tabs" role="tablist">
          <li className="username">
            {user ? (
              <div>{user.musicbrainz_id}</div>
            ) : (
              <div>
                <a href="/login">Sign in</a>
              </div>
            )}
          </li>
          <NavItem
            label="Listens"
            url={user ? `/user/${user.musicbrainz_id}/` : "#"}
            isActive={activeSection === ""}
            isDisabled={!user}
          />
          <NavItem
            label="Stats"
            url={user ? `/user/${user.musicbrainz_id}/stats/` : "/index/stats"}
            isActive={activeSection === "stats"}
          />
          <NavItem
            label="Taste"
            url={user ? `/user/${user.musicbrainz_id}/taste/` : "#"}
            isActive={activeSection === "taste"}
            isDisabled={!user}
          />
          <NavItem
            label="Playlists"
            url={user ? `/user/${user.musicbrainz_id}/playlists/` : "#"}
            isActive={activeSection === "playlists"}
            isDisabled={!user}
          />
          <NavItem
            label="Created for you"
            url={user ? `/user/${user.musicbrainz_id}/recommendations/` : "#"}
            isActive={activeSection === "recommendations"}
            isDisabled={!user}
          />
        </ul>
      </div>
      <Outlet />
    </>
  );
}

export default UserFeedLayout;
