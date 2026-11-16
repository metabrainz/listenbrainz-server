import * as React from "react";
import { Outlet } from "react-router";
import type { RouteObject } from "react-router";
import RouteLoader, { RouteQueryLoader } from "../utils/Loader";

const getIndexRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          index: true,
          lazy: {
            Component: async () => {
              return (await import("../home/Homepage")).HomePageWrapper;
            },
            loader: async () => {
              return RouteQueryLoader("home");
            },
          },
        },
        {
          path: "agree-to-terms/",
          lazy: {
            Component: async () => {
              return (await import("../gdpr/GDPR")).default;
            },
          },
        },
        {
          path: "import-data/",
          lazy: {
            Component: async () => {
              return (await import("../import-data/ImportData")).default;
            },
          },
        },
        {
          path: "lastfm-proxy/",
          lazy: {
            Component: async () => {
              return (await import("../lastfm-proxy/LastfmProxy")).default;
            },
          },
        },
        {
          path: "listens-offline/",
          lazy: {
            Component: async () => {
              return (await import("../listens-offline/ListensOffline"))
                .default;
            },
          },
        },
        {
          path: "musicbrainz-offline/",
          lazy: {
            Component: async () => {
              return (await import("../musicbrainz-offline/MusicBrainzOffline"))
                .default;
            },
          },
        },
        {
          path: "search/",
          lazy: {
            Component: async () => {
              return (await import("../search/Search")).default;
            },
          },
        },
        {
          path: "playlist/",
          lazy: {
            Component: async () => {
              return (await import("../layout/LayoutWithBackButton")).default;
            },
          },
          children: [
            {
              path: ":playlistID/",
              lazy: {
                Component: async () => {
                  return (await import("../playlists/Playlist")).default;
                },
                loader: async () => {
                  return RouteLoader;
                },
              },
            },
          ],
        },
        {
          path: "/statistics/",
          lazy: {
            Component: async () => {
              return (await import("../user/layout")).default;
            },
          },
          children: [
            {
              index: true,
              lazy: {
                Component: async () => {
                  return (await import("../user/stats/UserReports")).default;
                },
              },
            },
            {
              path: "top-artists/",
              lazy: {
                Component: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .default;
                },
                loader: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .StatisticsChartLoader;
                },
              },
            },
            {
              path: "top-albums/",
              lazy: {
                Component: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .default;
                },
                loader: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .StatisticsChartLoader;
                },
              },
            },
            {
              path: "top-tracks/",
              lazy: {
                Component: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .default;
                },
                loader: async () => {
                  return (await import("../user/charts/UserEntityChart"))
                    .StatisticsChartLoader;
                },
              },
            },
          ],
        },
        {
          path: "recent/",
          lazy: {
            Component: async () => {
              return (await import("../user-feed/UserFeedLayout")).default;
            },
          },
          children: [
            {
              index: true,
              lazy: {
                Component: async () => {
                  return (await import("../recent/RecentListens"))
                    .RecentListensWrapper;
                },
                loader: async () => {
                  return RouteLoader;
                },
              },
            },
          ],
        },
        {
          path: "api/auth/",
          lazy: {
            Component: async () => {
              return (await import("../api/auth/AuthPage")).default;
            },
          },
        },
        {
          path: "donors/",
          lazy: {
            Component: async () => {
              return (await import("../donors/Donors")).default;
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getIndexRoutes;
