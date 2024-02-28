import * as React from "react";
import { Outlet } from "react-router-dom";
import ImportData from "../import-data/ImportData";
import LastfmProxy from "../lastfm-proxy/LastfmProxy";
import ListensOffline from "../listens-offline/ListensOffline";
import MusicBrainzOffline from "../musicbrainz-offline/MusicBrainzOffline";
import SearchResults from "../search/UserSearch";
import MessyBrainz from "../messybrainz/MessyBrainz";
import RouteLoader from "../utils/Loader";
import { PlaylistPageWrapper } from "../playlists/Playlist";
import { PlayingNowPageWrapper } from "../metadata-viewer/MetadataViewerPage";
import HomePage from "../home/Homepage";
import Login from "../login/Login";
import GDPR from "../gdpr/GDPR";

const getIndexRoutes = () => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          index: true,
          element: <HomePage />,
          loader: RouteLoader,
        },
        {
          path: "login/",
          element: <Login />,
        },
        {
          path: "agree-to-terms/",
          element: <GDPR />,
        },
        {
          path: "import-data/",
          element: <ImportData />,
        },
        {
          path: "messybrainz/",
          element: <MessyBrainz />,
        },
        {
          path: "lastfm-proxy/",
          element: <LastfmProxy />,
        },
        {
          path: "listens-offline/",
          element: <ListensOffline />,
        },
        {
          path: "musicbrainz-offline/",
          element: <MusicBrainzOffline />,
        },
        {
          path: "search/",
          element: <SearchResults />,
          loader: RouteLoader,
        },
        {
          path: "playlist/:playlistID/",
          element: <PlaylistPageWrapper />,
          loader: RouteLoader,
        },
        {
          path: "listening-now/",
          element: <PlayingNowPageWrapper />,
          loader: RouteLoader,
        },
        {
          path: "/statistics/",
          lazy: async () => {
            const UserDashboardLayout = await import("../user/layout");
            return { Component: UserDashboardLayout.default };
          },
          children: [
            {
              index: true,
              lazy: async () => {
                const UserReports = await import("../user/stats/UserReports");
                return { Component: UserReports.StatisticsPage };
              },
            },
            {
              path: "top-artists/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../user/charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.StatisticsChartLoader,
                };
              },
            },
            {
              path: "top-albums/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../user/charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.StatisticsChartLoader,
                };
              },
            },
            {
              path: "top-tracks/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../user/charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.StatisticsChartLoader,
                };
              },
            },
          ],
        },
        {
          path: "/",
          lazy: async () => {
            const UserFeedLayout = await import("../user-feed/UserFeedLayout");
            return { Component: UserFeedLayout.default };
          },
          children: [
            {
              path: "/feed/",
              lazy: async () => {
                const UserFeed = await import("../user-feed/UserFeed");
                return { Component: UserFeed.default };
              },
            },
            {
              path: "/recent/",
              lazy: async () => {
                const RecentListens = await import("../recent/RecentListens");
                return {
                  Component: RecentListens.RecentListensWrapper,
                  loader: RecentListens.RecentListensLoader,
                };
              },
            },
          ],
        },
      ],
    },
  ];
  return routes;
};

export default getIndexRoutes;
