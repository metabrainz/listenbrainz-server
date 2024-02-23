import * as React from "react";
import { Outlet } from "react-router-dom";
import { PlayerPageWrapper } from "../PlayerPage";
import RouteLoader from "../../utils/Loader";

const getPlayerRoutes = () => {
  const routes = [
    {
      path: "/player/",
      element: <Outlet />,
      children: [
        {
          index: true,
          element: <PlayerPageWrapper />,
          loader: RouteLoader,
        },
        {
          path: "release/:releaseMBID",
          element: <PlayerPageWrapper />,
          loader: RouteLoader,
        },
      ],
    },
  ];
  return routes;
};

export default getPlayerRoutes;
