import * as React from "react";
import { Outlet } from "react-router";
import { RouteQueryLoader } from "../../utils/Loader";

const getPlayerRoutes = () => {
  const routes = [
    {
      path: "/player/",
      element: <Outlet />,
      children: [
        {
          index: true,
          lazy: {
            Component: async () => {
              return (await import("../PlayerPage")).PlayerPageWrapper;
            },
            loader: async () => {
              return RouteQueryLoader("player", true);
            },
          },
        },
        {
          path: "release/:releaseMBID",
          lazy: {
            Component: async () => {
              return (await import("../PlayerPage")).PlayerPageRedirectToAlbum;
            },
          },
        },
      ],
    },
  ];
  return routes;
};

export default getPlayerRoutes;
