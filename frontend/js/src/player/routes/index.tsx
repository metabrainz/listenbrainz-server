import * as React from "react";
import { Outlet } from "react-router-dom";
import { RouteQueryLoader } from "../../utils/Loader";

const getPlayerRoutes = () => {
  const routes = [
    {
      path: "/player/",
      element: <Outlet />,
      children: [
        {
          index: true,
          lazy: async () => {
            const PlayerPage = await import("../PlayerPage");
            return { Component: PlayerPage.PlayerPageWrapper };
          },
          loader: RouteQueryLoader("player", true),
        },
        {
          path: "release/:releaseMBID",
          lazy: async () => {
            const PlayerPage = await import("../PlayerPage");
            return { Component: PlayerPage.PlayerPageRedirectToAlbum };
          },
        },
      ],
    },
  ];
  return routes;
};

export default getPlayerRoutes;
