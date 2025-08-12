import * as React from "react";
import type { RouteObject } from "react-router";

const getFeedRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "feed/",
      lazy: {
        Component: async () => {
          return (await import("../UserFeedLayout")).default;
        },
      },
      children: [
        {
          index: true,
          lazy: {
            Component: async () => {
              return (await import("../UserFeed")).default;
            },
          },
        },
        {
          path: ":mode/",
          lazy: {
            Component: async () => {
              return (await import("../NetworkFeed")).default;
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getFeedRoutes;
