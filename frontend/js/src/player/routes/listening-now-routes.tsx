import * as React from "react";
import { Outlet } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import RouteLoader from "../../utils/Loader";

const getPlayingNowRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          path: "listening-now/",
          lazy: async () => {
            const PlayingNowPage = await import(
              "../../metadata-viewer/MetadataViewerPage"
            );
            return { Component: PlayingNowPage.PlayingNowPageWrapper };
          },
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getPlayingNowRoutes;
