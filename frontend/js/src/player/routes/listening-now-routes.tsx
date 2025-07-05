import * as React from "react";
import { Outlet } from "react-router";
import type { RouteObject } from "react-router";
import RouteLoader from "../../utils/Loader";

const getPlayingNowRoutes = (): RouteObject[] => {
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        {
          path: "listening-now/",
          lazy: {
            Component: async () => {
              return (await import("../../metadata-viewer/MetadataViewerPage"))
                .PlayingNowPageWrapper;
            },
            loader: async () => {
              return RouteLoader;
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getPlayingNowRoutes;
