import * as React from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

type NavbarLink = { to: string; label: string };

const links: NavbarLink[] = [
  { to: "fresh-releases/", label: "Fresh Releases" },
  { to: "huesound/", label: "Huesound" },
  { to: "cover-art-collage/2023/", label: "Cover Art Collage 2023" },
  { to: "cover-art-collage/2022/", label: "Cover Art Collage 2022" },
  { to: "cover-art-collage/", label: "Cover Art Collage 2023" },
  { to: "music-neighborhood/", label: "Music Neighborhood" },
  { to: "similar-users/", label: "Similar Users" },
  { to: "lb-radio/", label: "LB Radio" },
  { to: "art-creator/", label: "Art Creator" },
];

function ExploreLayout() {
  const location = useLocation();
  const [activeLabel, setActiveLabel] = React.useState<string>("");

  const getActiveLabel = React.useCallback((path: string) => {
    const newActiveLabel = links.find((link) => path.includes(link.to))?.label;
    return newActiveLabel;
  }, []);

  React.useEffect(() => {
    const newActiveLabel = getActiveLabel(location.pathname);
    setActiveLabel(newActiveLabel || "");
  }, [location.pathname, getActiveLabel]);

  return (
    <>
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/explore/">Explore</Link>
          </li>
          {activeLabel && <li className="active">{activeLabel}</li>}
        </ol>
      </div>
      <Outlet />
    </>
  );
}

export default ExploreLayout;
