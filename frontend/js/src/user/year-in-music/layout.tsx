import * as React from "react";
import { Link, Outlet, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import tinycolor from "tinycolor2";

import queryClient from "../../utils/QueryClient";
import { RouteQuery } from "../../utils/Loader";
import { getYearColors, LATEST_YEAR_IN_MUSIC_YEAR } from "./YearInMusic";
import { YIMSEO } from "./SEO";
import YIMYearSelection from "./components/YIMYearSelection";
import Loader from "../../components/Loader";

export type YearInMusicLayoutData = {
  year: number;
  cover_art: {
    caa_id: number;
    caa_release_mbid: string;
  };
};

type YearInMusicLayoutProps = {
  user: ListenBrainzUser;
  data: YearInMusicLayoutData[];
};

function YearInMusicLayout() {
  const params = useParams();
  const { year: yearParam, username } = params as {
    year: string;
    username: string;
  };
  const year = Number(yearParam) || LATEST_YEAR_IN_MUSIC_YEAR;

  const loaderUrl = `/user/${username}/year-in-music/`;
  const { data, isLoading } = useQuery<YearInMusicLayoutProps>(
    RouteQuery([`year-in-music-layout`, username], loaderUrl)
  );

  const fallbackUser = { name: username ?? "" };
  const { user = fallbackUser, data: yearInMusicData = [] } = data || {};
  const encodedUsername = encodeURIComponent(user.name);

  const gradientColors = getYearColors(year);
  const textColor = "#F1F2E1";
  const cardBackgroundColor = textColor;

  return (
    <>
      <YIMSEO year={year} userName={user.name} />
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/explore/">Explore</Link>
          </li>
          <li className="active">Year in Music</li>
        </ol>
      </div>
      <div
        id="year-in-music"
        style={{
          ["--cardBackgroundColor" as any]: cardBackgroundColor,
          ["--accentColor" as any]: tinycolor
            .mostReadable(cardBackgroundColor, gradientColors, {
              includeFallbackColors: false,
            })
            .darken(5)
            .saturate(5)
            .toHexString(),
          ["--gradientColor1" as any]: gradientColors[0],
          ["--gradientColor2" as any]: gradientColors[1],
        }}
      >
        <Loader className="loader-container" isLoading={isLoading} />
        <div>
          <div id="main-header">
            <div className="user-name">{user.name}&apos;s</div>
            <div className="header-image">
              <img
                src="/static/img/year-in-music/header.png"
                alt="Year in Music"
                className="w-100"
                style={{ opacity: 0.2 }}
              />
              <img
                src="/static/img/year-in-music/header.png"
                alt="Year in Music"
                className="w-100"
                style={{ mixBlendMode: "overlay" }}
              />
            </div>
          </div>
          <YIMYearSelection
            year={year}
            encodedUsername={encodedUsername}
            data={yearInMusicData}
          />
          <Outlet />
        </div>
      </div>
      {/* Trick to load the font files for use with the SVG render CHECK IF THIS IS STILL REQUIRED */}
      <span
        style={{
          fontFamily: "Inter, sans-serif",
          opacity: 0,
          position: "fixed",
        }}
      >
        x
      </span>
    </>
  );
}

export const routeQueryLoader = async ({
  params,
}: {
  params: { username?: string };
}) => {
  const { username } = params;
  if (!username) {
    return null;
  }
  const url = `/user/${username}/year-in-music/`;

  await queryClient.ensureQueryData({
    ...RouteQuery(["year-in-music-layout", username], url),
  });
  return null;
};

export default YearInMusicLayout;
