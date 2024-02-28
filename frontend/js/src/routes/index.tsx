import * as React from "react";

const getStatisticsRoutes = () => {
  const routes = [
    {
      path: "/statistics/",
      lazy: async () => {
        const UserDashboardLayout = await import("../user/layout");
        return { Component: UserDashboardLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const UserReports = await import("../user/stats/UserReports");
            return { Component: UserReports.StatisticsPage };
          },
        },
        {
          path: "top-artists/",
          lazy: async () => {
            const UserEntityChart = await import(
              "../user/charts/UserEntityChart"
            );
            return {
              Component: UserEntityChart.default,
              loader: UserEntityChart.StatisticsChartLoader,
            };
          },
        },
        {
          path: "top-albums/",
          lazy: async () => {
            const UserEntityChart = await import(
              "../user/charts/UserEntityChart"
            );
            return {
              Component: UserEntityChart.default,
              loader: UserEntityChart.StatisticsChartLoader,
            };
          },
        },
        {
          path: "top-tracks/",
          lazy: async () => {
            const UserEntityChart = await import(
              "../user/charts/UserEntityChart"
            );
            return {
              Component: UserEntityChart.default,
              loader: UserEntityChart.StatisticsChartLoader,
            };
          },
        },
      ],
    },
    {
      path: "/",
      lazy: async () => {
        const UserFeedLayout = await import("../user-feed/UserFeedLayout");
        return { Component: UserFeedLayout.default };
      },
      children: [
        {
          path: "/feed/",
          lazy: async () => {
            const UserFeed = await import("../user-feed/UserFeed");
            return { Component: UserFeed.default };
          },
        },
        {
          path: "/recent/",
          lazy: async () => {
            const RecentListens = await import("../recent/RecentListens");
            return {
              Component: RecentListens.RecentListensWrapper,
              loader: RecentListens.RecentListensLoader,
            };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getStatisticsRoutes;
