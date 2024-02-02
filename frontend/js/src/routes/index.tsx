import * as React from "react";
import UserEntityChart, {
  StatisticsChartLoader,
} from "../user/charts/UserEntityChart";
import { StatisticsPage } from "../user/stats/UserReports";
import UserDashboardLayout from "../user/layout";
import UserFeedPage from "../user-feed/UserFeed";
import {
  RecentListensLoader,
  RecentListensWrapper,
} from "../recent/RecentListens";
import UserFeedLayout from "../user-feed/UserFeedLayout";

const getStatisticsRoutes = () => {
  const routes = [
    {
      path: "/statistics/",
      element: <UserDashboardLayout />,
      children: [
        {
          index: true,
          element: <StatisticsPage />,
        },
        {
          path: "top-artists/",
          element: <UserEntityChart />,
          loader: StatisticsChartLoader,
        },
        {
          path: "top-albums/",
          element: <UserEntityChart />,
          loader: StatisticsChartLoader,
        },
        {
          path: "top-tracks/",
          element: <UserEntityChart />,
          loader: StatisticsChartLoader,
        },
      ],
    },
    {
      path: "/",
      element: <UserFeedLayout />,
      children: [
        {
          path: "/feed/",
          element: <UserFeedPage events={[]} />,
        },
        {
          path: "/recent/",
          element: <RecentListensWrapper />,
          loader: RecentListensLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getStatisticsRoutes;
