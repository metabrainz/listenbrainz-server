import * as React from "react";

import { Navigate, Outlet } from "react-router-dom";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import { UserReportsLoader, UserReportsWrapper } from "../../stats/UserReports";
import UserFeedLayout from "../layout";
import { ListensLoader, ListensWrapper } from "../pages";
import { UserTasteLoader, UserTastesWrapper } from "../UserTaste";
import {
  UserPlaylistsLoader,
  UserPlaylistsWrapper,
} from "../../playlists/Playlists";
import {
  RecommendationsPageLoader,
  RecommendationsPageWrapper,
} from "../../recommendations/RecommendationsPage";
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

const getUserRoutes = () => {
  const ListensWithAlertNotifications = withAlertNotifications(ListensWrapper);
  const UserReportsPageWithAlertNotifications = withAlertNotifications(
    UserReportsWrapper
  );
  const UserTasteWithAlertNotifications = withAlertNotifications(
    UserTastesWrapper
  );
  const UserPlaylistsWithAlertNotifications = withAlertNotifications(
    UserPlaylistsWrapper
  );
  const RecommendationsPageWithAlertNotifications = withAlertNotifications(
    RecommendationsPageWrapper
  );

  const YearInMusic2021WithAlertNotifications = withAlertNotifications(
    YearInMusic2021Wrapper
  );
  const YearInMusic2022WithAlertNotifications = withAlertNotifications(
    YearInMusic2022Wrapper
  );
  const YearInMusic2023WithAlertNotifications = withAlertNotifications(
    YearInMusic2023Wrapper
  );

  const routes = [
    {
      path: "/user/:username/",
      element: <UserFeedLayout />,
      children: [
        {
          index: true,
          element: <ListensWithAlertNotifications />,
          loader: ListensLoader,
        },
        {
          path: "stats/",
          element: <UserReportsPageWithAlertNotifications />,
          loader: UserReportsLoader,
        },
        {
          path: "reports/",
          element: <Navigate to="stats/" replace />,
        },
        {
          path: "taste/",
          element: <UserTasteWithAlertNotifications />,
          loader: UserTasteLoader,
        },
        {
          path: "playlists/",
          element: <UserPlaylistsWithAlertNotifications />,
          loader: UserPlaylistsLoader,
        },
        {
          path: "collaborations/",
          element: <Navigate to="playlists/" />,
        },
        {
          path: "recommendations/",
          element: <RecommendationsPageWithAlertNotifications />,
          loader: RecommendationsPageLoader,
        },
        {
          path: "year-in-music/",
          element: <Outlet />,
          children: [
            {
              index: true,
              element: <YearInMusic2023WithAlertNotifications />,
              loader: YearInMusic2023Loader,
            },
            {
              path: "2023/",
              element: <YearInMusic2023WithAlertNotifications />,
              loader: YearInMusic2023Loader,
            },
            {
              path: "2022/",
              element: <YearInMusic2022WithAlertNotifications />,
              loader: YearInMusic2022Loader,
            },
            {
              path: "2021/",
              element: <YearInMusic2021WithAlertNotifications />,
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
