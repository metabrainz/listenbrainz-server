import * as React from "react";
import { Link, Outlet, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import tinycolor from "tinycolor2";
import { getYear } from "date-fns";

import queryClient from "../../utils/QueryClient";
import { RouteQuery } from "../../utils/Loader";
import { getYearColors } from "./YearInMusic";
import SEO, { YIMYearMetaTags } from "./SEO";
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

const getLoaderURL = () => {
  const match = window.location.pathname.match(
    /^\/user\/([^/]+)\/year-in-music(?:\/([^/]+))?\/?$/
  );
  if (!match) {
    throw new Error("Invalid year-in-music URL");
  }
  const [, username] = match;
  return new URL(`/user/${username}/year-in-music/`, window.location.origin);
};

function YearInMusicLayout() {
  const { year: yearParam, userName } = useParams<{
    year: string;
    userName: string;
  }>();
  const year = Number(yearParam) || getYear(Date.now());

  const loaderUrl = getLoaderURL();
  const { data, isLoading } = useQuery<YearInMusicLayoutProps>(
    RouteQuery([`year-in-music-layout`], loaderUrl.toString())
  );

  const fallbackUser = { name: userName ?? "" };
  const { user = fallbackUser, data: yearInMusicData = [] } = data || {};
  const encodedUsername = encodeURIComponent(user.name);

  const gradientColors = getYearColors(year);
  const textColor = "#F1F2E1";
  const cardBackgroundColor = textColor;

  return (
    <>
      <SEO year={year} userName={user.name} />
      <YIMYearMetaTags />
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

export const routeQueryLoader = async () => {
  const url = getLoaderURL();

  await queryClient.ensureQueryData({
    ...RouteQuery(["year-in-music-layout"], url.toString()),
  });
  return null;
};

export default YearInMusicLayout;
