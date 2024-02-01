import * as React from "react";

import { Outlet } from "react-router-dom";
import getExploreRoutes from "../explore/routes";
import getUserRedirectRoutes from "../user/routes/redirectRoutes";
import getUserRoutes from "../user/routes/userRoutes";

const getRoutes = (musicbrainzID?: string) => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);
  const routes = [
    {
      path: "/",
      element: <Outlet />,
      children: [...exploreRoutes, ...userRoutes, ...redirectRoutes],
    },
  ];

  return routes;
};

export default getRoutes;
