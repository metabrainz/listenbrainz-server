import * as React from "react";
import { Outlet } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import RouteLoader, { RouteQueryLoader } from "../utils/Loader";

const getIndexRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          index: true,
          lazy: async () => {
            const HomePage = await import("../home/Homepage");
            return { Component: HomePage.HomePageWrapper };
          },
          loader: RouteQueryLoader("home"),
        },
        {
          path: "login/",
          lazy: async () => {
            const Login = await import("../login/Login");
            return { Component: Login.default };
          },
        },
        {
          path: "agree-to-terms/",
          lazy: async () => {
            const GDPR = await import("../gdpr/GDPR");
            return { Component: GDPR.default };
          },
        },
        {
          path: "import-data/",
          lazy: async () => {
            const ImportData = await import("../import-data/ImportData");
            return { Component: ImportData.default };
          },
        },
        {
          path: "messybrainz/",
          lazy: async () => {
            const MessyBrainz = await import("../messybrainz/MessyBrainz");
            return { Component: MessyBrainz.default };
          },
        },
        {
          path: "lastfm-proxy/",
          lazy: async () => {
            const LastfmProxy = await import("../lastfm-proxy/LastfmProxy");
            return { Component: LastfmProxy.default };
          },
        },
        {
          path: "listens-offline/",
          lazy: async () => {
            const ListensOffline = await import(
              "../listens-offline/ListensOffline"
            );
            return { Component: ListensOffline.default };
          },
        },
        {
          path: "musicbrainz-offline/",
          lazy: async () => {
            const MusicBrainzOffline = await import(
              "../musicbrainz-offline/MusicBrainzOffline"
            );
            return { Component: MusicBrainzOffline.default };
          },
        },
        {
          path: "search/",
          lazy: async () => {
            const SearchResults = await import("../search/Search");
            return { Component: SearchResults.default };
          },
        },
        {
          path: "playlist/",
          lazy: async () => {
            const LayoutWithBackButton = await import(
              "../layout/LayoutWithBackButton"
            );
            return { Component: LayoutWithBackButton.default };
          },
          children: [
            {
              path: ":playlistID/",
              lazy: async () => {
                const PlaylistPage = await import("../playlists/Playlist");
                return { Component: PlaylistPage.default };
              },
              loader: RouteLoader,
            },
          ],
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
                return { Component: UserReports.default };
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
          path: "recent/",
          lazy: async () => {
            const UserFeedLayout = await import("../user-feed/UserFeedLayout");
            return { Component: UserFeedLayout.default };
          },
          children: [
            {
              index: true,
              lazy: async () => {
                const RecentListens = await import("../recent/RecentListens");
                return {
                  Component: RecentListens.RecentListensWrapper,
                };
              },
              loader: RouteLoader,
            },
          ],
        },
        {
          path: "api/auth/",
          lazy: async () => {
            const APIAuth = await import("../api/auth/AuthPage");
            return { Component: APIAuth.default };
          },
        },
        {
          path: "donors/",
          lazy: async () => {
            const Donors = await import("../donors/Donors");
            return { Component: Donors.default };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getIndexRoutes;
