import * as React from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

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
  { to: "year-in-music/2024/", label: "Year in Music 2024" },
  { to: "year-in-music/2023/", label: "Year in Music 2023" },
  { to: "year-in-music/2022/", label: "Year in Music 2022" },
  { to: "year-in-music/2021/", label: "Year in Music 2021" },
  { to: "year-in-music/", label: "Year in Music 2024" },
  { to: "ai-brainz/", label: "AI Brainz" },
];

function ExploreLayout() {
  const location = useLocation();
  const activeLabel = links.find((link) => location.pathname.includes(link.to))
    ?.label;

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
