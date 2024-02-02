import * as React from "react";
import UserEntityChart, {
  StatisticsChartLoader,
} from "../user/charts/UserEntityChart";
import { StatisticsPage } from "../user/stats/UserReports";
import UserFeedLayout from "../user/layout";

const getStatisticsRoutes = () => {
  const routes = [
    {
      path: "/statistics/",
      element: <UserFeedLayout />,
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
  ];
  return routes;
};

export default getStatisticsRoutes;
