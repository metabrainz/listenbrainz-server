import * as React from "react";

import type { RouteObject } from "react-router-dom";
import getExploreRoutes from "../explore/routes";
import getUserRedirectRoutes from "../user/routes/redirectRoutes";
import getUserRoutes from "../user/routes/userRoutes";
import getIndexRoutes from ".";
import getAboutRoutes from "../about/routes";
import getRedirectRoutes from "./redirectRoutes";
import getEntityPages from "./EntityPages";
import Layout from "../layout";
import ErrorBoundary from "../error/ErrorBoundary";
import getFeedRoutes from "../user-feed/routes";
import getSettingsRoutes from "../settings/routes";
import getSettingsRedirectRoutes from "../settings/routes/redirectRoutes";
import getPlayerRoutes from "../player/routes";
import getRecommendationsRoutes from "../recommended/tracks/routes";
import getPlayingNowRoutes from "../player/routes/listening-now-routes";

const getRoutes = (
  musicbrainzID?: string,
  withBrainzPlayer?: boolean
): RouteObject[] => {
  const exploreRoutes = getExploreRoutes();
  const userRoutes = getUserRoutes();
  const redirectRoutes = getUserRedirectRoutes(musicbrainzID);
  const aboutRoutes = getAboutRoutes();
  const aboutRedirectRoutes = getRedirectRoutes();
  const entityPages = getEntityPages();
  const indexRoutes = getIndexRoutes();
  const feedRoutes = getFeedRoutes();
  const settingsRoutes = getSettingsRoutes();
  const settingsRedirectRoutes = getSettingsRedirectRoutes();
  const playerRoutes = getPlayerRoutes();
  const recommendationsRoutes = getRecommendationsRoutes();
  const playingNowRoutes = getPlayingNowRoutes();

  const routes = [
    {
      path: "/",
      element: <Layout withBrainzPlayer={withBrainzPlayer} />,
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
        ...playerRoutes,
        ...recommendationsRoutes,
      ],
    },
    {
      element: (
        <Layout withProtectedRoutes withBrainzPlayer={withBrainzPlayer} />
      ),
      errorElement: (
        <Layout>
          <ErrorBoundary />
        </Layout>
      ),
      children: [
        ...feedRoutes,
        ...settingsRoutes,
        ...settingsRedirectRoutes,
        ...playingNowRoutes,
      ],
    },
  ];

  return routes;
};

export default getRoutes;
