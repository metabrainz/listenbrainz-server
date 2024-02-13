import * as React from "react";

import getExploreRoutes from "../explore/routes";
import getUserRedirectRoutes from "../user/routes/redirectRoutes";
import getUserRoutes from "../user/routes/userRoutes";
import getIndexRoutes from ".";
import getAboutRoutes from "../about/routes";
import getRedirectRoutes from "./redirectRoutes";
import getEntityPages from "./EntityPages";
import Layout from "../layout";
import ErrorBoundary from "../error/ErrorBoundary";

const getRoutes = (musicbrainzID?: string) => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);
  const aboutRoutes = getAboutRoutes();
  const aboutRedirectRoutes = getRedirectRoutes();
  const entityPages = getEntityPages();
  const indexRoutes = getIndexRoutes();

  const routes = [
    {
      path: "/",
      element: <Layout />,
      errorElement: <ErrorBoundary />,
      children: [
        ...indexRoutes,
        ...aboutRoutes,
        ...aboutRedirectRoutes,
        ...entityPages,
        ...exploreRoutes,
        ...userRoutes,
        ...redirectRoutes,
      ],
    },
  ];

  return routes;
};

export default getRoutes;
