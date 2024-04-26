import * as React from "react";

import { Navigate, Outlet } from "react-router-dom";
import RouteLoader from "../../utils/Loader";

const getUserRoutes = () => {
  const routes = [
    {
      path: "/user/:username/",
      lazy: async () => {
        const DashboardLayout = await import("../layout");
        return { Component: DashboardLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const Listens = await import("../Dashboard");
            return { Component: Listens.ListensWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "stats/",
          element: <Outlet />,
          children: [
            {
              index: true,
              lazy: async () => {
                const UserReports = await import("../stats/UserReports");
                return { Component: UserReports.UserReportsWrapper };
              },
              loader: RouteLoader,
            },
            {
              path: "top-artists/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.UserEntityChartLoader,
                };
              },
            },
            {
              path: "top-albums/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.UserEntityChartLoader,
                };
              },
            },
            {
              path: "top-tracks/",
              lazy: async () => {
                const UserEntityChart = await import(
                  "../charts/UserEntityChart"
                );
                return {
                  Component: UserEntityChart.default,
                  loader: UserEntityChart.UserEntityChartLoader,
                };
              },
            },
          ],
        },
        {
          path: "history/",
          element: <Navigate to="../stats/top-artists/" />,
        },
        {
          path: "artists/",
          element: <Navigate to="../stats/top-artists/" />,
        },
        {
          path: "reports/",
          element: <Navigate to="../stats/" replace />,
        },
        {
          path: "taste/",
          lazy: async () => {
            const UserTastes = await import("../taste/UserTaste");
            return { Component: UserTastes.UserTastesWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "playlists/",
          lazy: async () => {
            const UserPlaylists = await import("../playlists/Playlists");
            return { Component: UserPlaylists.UserPlaylistsWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "collaborations/",
          element: <Navigate to="playlists/" />,
        },
        {
          path: "recommendations/",
          lazy: async () => {
            const RecommendationsPage = await import(
              "../recommendations/RecommendationsPage"
            );
            return {
              Component: RecommendationsPage.RecommendationsPageWrapper,
            };
          },
          loader: RouteLoader,
        },
      ],
    },
    {
      path: "/user/:username/year-in-music/",
      lazy: async () => {
        const ExploreLayout = await import("../../explore/layout");
        return { Component: ExploreLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const YearInMusic2023 = await import(
              "../year-in-music/2023/YearInMusic2023"
            );
            return { Component: YearInMusic2023.YearInMusicWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "2023/",
          lazy: async () => {
            const YearInMusic2023 = await import(
              "../year-in-music/2023/YearInMusic2023"
            );
            return { Component: YearInMusic2023.YearInMusicWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "2022/",
          lazy: async () => {
            const YearInMusic2022 = await import(
              "../year-in-music/2022/YearInMusic2022"
            );
            return { Component: YearInMusic2022.YearInMusicWrapper };
          },
          loader: RouteLoader,
        },
        {
          path: "2021/",
          lazy: async () => {
            const YearInMusic2021 = await import(
              "../year-in-music/2021/YearInMusic2021"
            );
            return { Component: YearInMusic2021.YearInMusicWrapper };
          },
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getUserRoutes;
