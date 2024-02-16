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
import ProtectedRoutes from "../utils/ProtectedRoutes";
import getSettingsRoutes from "../settings/routes";
import getSettingsRedirectRoutes from "../settings/routes/redirectRoutes";

const getRoutes = (musicbrainzID?: string) => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);
  const aboutRoutes = getAboutRoutes();
  const aboutRedirectRoutes = getRedirectRoutes();
  const entityPages = getEntityPages();
  const indexRoutes = getIndexRoutes();
  const settingsRoutes = getSettingsRoutes();
  const settingsRedirectRoutes = getSettingsRedirectRoutes();

  const routes = [
    {
      path: "/",
      element: <Layout />,
      errorElement: (
        <Layout>
          <ErrorBoundary />
        </Layout>
      ),
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
    {
      element: <ProtectedRoutes />,
      errorElement: (
        <Layout>
          <ErrorBoundary />
        </Layout>
      ),
      children: [...settingsRoutes, ...settingsRedirectRoutes],
    },
  ];

  return routes;
};

export default getRoutes;
