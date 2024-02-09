import * as React from "react";

import { Outlet } from "react-router-dom";
import getIndexRoutes from ".";
import getAboutRoutes from "../about/routes";
import getRedirectRoutes from "./redirectRoutes";
import getEntityPages from "./EntityPages";
import ErrorBoundary from "../error/ErrorBoundary";

const getRoutes = () => {
  const indexRoutes = getIndexRoutes();
  const aboutRoutes = getAboutRoutes();
  const aboutRedirectRoutes = getRedirectRoutes();
  const entityPages = getEntityPages();

  const routes = [
    {
      path: "/",
      element: <Outlet />,
      errorElement: <ErrorBoundary />,
      children: [
        ...indexRoutes,
        ...aboutRoutes,
        ...aboutRedirectRoutes,
        ...entityPages,
      ],
    },
  ];

  return routes;
};

export default getRoutes;
