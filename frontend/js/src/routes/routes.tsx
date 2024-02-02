import * as React from "react";

import { Outlet } from "react-router-dom";
import getExploreRoutes from "../explore/routes";
import getUserRedirectRoutes from "../user/routes/redirectRoutes";
import getUserRoutes from "../user/routes/userRoutes";
import getStatisticsRoutes from ".";

const getRoutes = (musicbrainzID?: string) => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);

  const statisticsRoutes = getStatisticsRoutes();
  const indexRoutes = [...statisticsRoutes];

  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [
        ...indexRoutes,
        ...exploreRoutes,
        ...userRoutes,
        ...redirectRoutes,
      ],
    },
  ];

  return routes;
};

export default getRoutes;
