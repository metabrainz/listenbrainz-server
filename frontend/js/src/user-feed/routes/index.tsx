import * as React from "react";
import type { RouteObject } from "react-router-dom";

const getFeedRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "feed/",
      lazy: async () => {
        const UserFeedLayout = await import("../UserFeedLayout");
        return { Component: UserFeedLayout.default };
      },
      children: [
        {
          index: true,
          lazy: async () => {
            const UserFeed = await import("../UserFeed");
            return { Component: UserFeed.default };
          },
        },
        {
          path: ":mode/",
          lazy: async () => {
            const NetworkFeed = await import("../NetworkFeed");
            return { Component: NetworkFeed.default };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getFeedRoutes;
