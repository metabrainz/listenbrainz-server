import * as React from "react";

import getExploreRoutes from "../explore/routes";
import getUserRedirectRoutes from "../user/routes/redirectRoutes";
import getUserRoutes from "../user/routes/userRoutes";
import getStatisticsRoutes from ".";
import Layout from "../layout";
import ErrorBoundary from "../error/ErrorBoundary";

const getRoutes = (musicbrainzID?: string) => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);

  const statisticsRoutes = getStatisticsRoutes();
  const indexRoutes = [...statisticsRoutes];

  const routes = [
    {
      path: "/",
      element: <Layout />,
      errorElement: <ErrorBoundary />,
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
