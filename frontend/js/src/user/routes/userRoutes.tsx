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
import UserEntityChart, {
  UserEntityChartLoader,
} from "../charts/UserEntityChart";
import ExploreLayout from "../../explore/layout";

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
            {
              path: "top-artists/",
              element: <UserEntityChart />,
              loader: UserEntityChartLoader,
            },
            {
              path: "top-albums/",
              element: <UserEntityChart />,
              loader: UserEntityChartLoader,
            },
            {
              path: "top-tracks/",
              element: <UserEntityChart />,
              loader: UserEntityChartLoader,
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
      ],
    },
    {
      path: "/user/:username/year-in-music/",
      element: <ExploreLayout />,
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
  ];
  return routes;
};

export default getUserRoutes;
