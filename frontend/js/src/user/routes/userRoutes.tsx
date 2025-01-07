import * as React from "react";

import { Navigate, Outlet } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import RouteLoader, { RouteQueryLoader } from "../../utils/Loader";

const getUserRoutes = (): RouteObject[] => {
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
            return { Component: Listens.default };
          },
          loader: RouteQueryLoader("dashboard", true),
        },
        {
          path: "stats/",
          element: <Outlet />,
          children: [
            {
              index: true,
              lazy: async () => {
                const UserReports = await import("../stats/UserReports");
                return { Component: UserReports.default };
              },
              loader: RouteLoader,
              shouldRevalidate: () => false,
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
          element: <Navigate to="../stats/top-artists/" replace />,
        },
        {
          path: "artists/",
          element: <Navigate to="../stats/top-artists/" replace />,
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
          element: <Navigate to="playlists/" replace />,
        },
        {
          path: "recommendations/",
          lazy: async () => {
            const RecommendationsPage = await import(
              "../recommendations/RecommendationsPage"
            );
            return {
              Component: RecommendationsPage.default,
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
          element: <Navigate to="./2024" replace />,
        },
        {
          path: "2024/",
          lazy: async () => {
            const YearInMusic2024 = await import(
              "../year-in-music/2024/YearInMusic2024"
            );
            return { Component: YearInMusic2024.YearInMusicWrapper };
          },
          loader: RouteQueryLoader("year-in-music-2024"),
        },
        {
          path: "2023/",
          lazy: async () => {
            const YearInMusic2023 = await import(
              "../year-in-music/2023/YearInMusic2023"
            );
            return { Component: YearInMusic2023.YearInMusicWrapper };
          },
          loader: RouteQueryLoader("year-in-music-2023"),
        },
        {
          path: "2022/",
          lazy: async () => {
            const YearInMusic2022 = await import(
              "../year-in-music/2022/YearInMusic2022"
            );
            return { Component: YearInMusic2022.YearInMusicWrapper };
          },
          loader: RouteQueryLoader("year-in-music-2022"),
        },
        {
          path: "2021/",
          lazy: async () => {
            const YearInMusic2021 = await import(
              "../year-in-music/2021/YearInMusic2021"
            );
            return { Component: YearInMusic2021.YearInMusicWrapper };
          },
          loader: RouteQueryLoader("year-in-music-2021"),
        },
      ],
    },
  ];
  return routes;
};

export default getUserRoutes;
