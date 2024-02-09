import * as React from "react";

import { Navigate, Outlet } from "react-router-dom";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import { UserReportsWrapper } from "../stats/UserReports";
import UserFeedLayout from "../layout";
import { ListensWrapper } from "../Dashboard";
import { UserTastesWrapper } from "../taste/UserTaste";
import { UserPlaylistsWrapper } from "../playlists/Playlists";
import { RecommendationsPageWrapper } from "../recommendations/RecommendationsPage";
import { YearInMusicWrapper as YearInMusic2021Wrapper } from "../year-in-music/2021/YearInMusic2021";
import { YearInMusicWrapper as YearInMusic2022Wrapper } from "../year-in-music/2022/YearInMusic2022";
import { YearInMusicWrapper as YearInMusic2023Wrapper } from "../year-in-music/2023/YearInMusic2023";
import UserEntityChart, {
  UserEntityChartLoader,
} from "../charts/UserEntityChart";
import ExploreLayout from "../../explore/layout";
import RouteLoader from "../../utils/Loader";

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
          loader: RouteLoader,
        },
        {
          path: "stats/",
          element: <Outlet />,
          children: [
            {
              index: true,
              element: <UserReportsWrapper />,
              loader: RouteLoader,
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
          loader: RouteLoader,
        },
        {
          path: "playlists/",
          element: <UserPlaylistsWrapper />,
          loader: RouteLoader,
        },
        {
          path: "collaborations/",
          element: <Navigate to="playlists/" />,
        },
        {
          path: "recommendations/",
          element: <RecommendationsPageWrapper />,
          loader: RouteLoader,
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
          loader: RouteLoader,
        },
        {
          path: "2023/",
          element: <YearInMusic2023Wrapper />,
          loader: RouteLoader,
        },
        {
          path: "2022/",
          element: <YearInMusic2022Wrapper />,
          loader: RouteLoader,
        },
        {
          path: "2021/",
          element: <YearInMusic2021Wrapper />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getUserRoutes;
