import * as React from "react";

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
          path: "recommendations/",
          element: <RecommendationsPageWithAlertNotifications />,
          loader: RecommendationsPageLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getUserRoutes;
