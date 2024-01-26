import * as React from "react";

import { Navigate, Outlet } from "react-router-dom";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import { UserReportsLoader, UserReportsWrapper } from "../stats/UserReports";
import UserFeedLayout from "../layout";
import { ListensLoader, ListensWrapper } from "../Dashboard";
import { UserTasteLoader, UserTastesWrapper } from "../taste/UserTaste";
import {
  UserPlaylistsLoader,
  UserPlaylistsWrapper,
} from "../playlists/Playlists";
import {
  RecommendationsPageLoader,
  RecommendationsPageWrapper,
} from "../recommendations/RecommendationsPage";
import {
  YearInMusicWrapper as YearInMusic2021Wrapper,
  YearInMusicLoader as YearInMusic2021Loader,
} from "../year-in-music/2021/YearInMusic2021";
import {
  YearInMusicWrapper as YearInMusic2022Wrapper,
  YearInMusicLoader as YearInMusic2022Loader,
} from "../year-in-music/2022/YearInMusic2022";
import {
  YearInMusicWrapper as YearInMusic2023Wrapper,
  YearInMusicLoader as YearInMusic2023Loader,
} from "../year-in-music/2023/YearInMusic2023";
import {
  UserEntityChartLoader,
  UserEntityChartWrapper,
} from "../charts/UserEntityChart";

const getUserRoutes = () => {
  const LayoutWithAlertNotifications = withAlertNotifications(UserFeedLayout);

  const routes = [
    {
      path: "/user/:username/",
      element: <LayoutWithAlertNotifications />,
      children: [
        {
          index: true,
          element: <ListensWrapper />,
          loader: ListensLoader,
        },
        {
          path: "stats/",
          element: <Outlet />,
          children: [
            {
              index: true,
              element: <UserReportsWrapper />,
              loader: UserReportsLoader,
            },
          ],
        },
        {
          path: "charts/",
          element: <UserEntityChartWrapper />,
          loader: UserEntityChartLoader,
        },
        {
          path: "reports/",
          element: <Navigate to="stats/" replace />,
        },
        {
          path: "taste/",
          element: <UserTastesWrapper />,
          loader: UserTasteLoader,
        },
        {
          path: "playlists/",
          element: <UserPlaylistsWrapper />,
          loader: UserPlaylistsLoader,
        },
        {
          path: "collaborations/",
          element: <Navigate to="playlists/" />,
        },
        {
          path: "recommendations/",
          element: <RecommendationsPageWrapper />,
          loader: RecommendationsPageLoader,
        },
        {
          path: "year-in-music/",
          element: <Outlet />,
          children: [
            {
              index: true,
              element: <YearInMusic2023Wrapper />,
              loader: YearInMusic2023Loader,
            },
            {
              path: "2023/",
              element: <YearInMusic2023Wrapper />,
              loader: YearInMusic2023Loader,
            },
            {
              path: "2022/",
              element: <YearInMusic2022Wrapper />,
              loader: YearInMusic2022Loader,
            },
            {
              path: "2021/",
              element: <YearInMusic2021Wrapper />,
              loader: YearInMusic2021Loader,
            },
          ],
        },
      ],
    },
  ];
  return routes;
};

export default getUserRoutes;
