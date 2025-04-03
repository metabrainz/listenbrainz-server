import * as React from "react";
import * as Sentry from "@sentry/react";
import { createRoot } from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  createRoutesFromChildren,
  matchRoutes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { Helmet } from "react-helmet";
import ErrorBoundary from "./utils/ErrorBoundary";
import GlobalAppContext from "./utils/GlobalAppContext";
import { getPageProps } from "./utils/utils";
import getRoutes from "./routes/routes";
import queryClient from "./utils/QueryClient";
import ReactQueryDevtool from "./utils/ReactQueryDevTools";
import { BrainzPlayerProvider } from "./common/brainzplayer/BrainzPlayerContext";

document.addEventListener("DOMContentLoaded", async () => {
  const { domContainer, globalAppContext, sentryProps } = await getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [
        Sentry.reactRouterV6BrowserTracingIntegration({
          useEffect: React.useEffect,
          useLocation,
          useNavigationType,
          createRoutesFromChildren,
          matchRoutes,
        }),
      ],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { currentUser } = globalAppContext;

  const brainzPlayerDisabled =
    globalAppContext?.userPreferences?.brainzplayer?.brainzplayerEnabled ===
    false;

  const routes = getRoutes(currentUser?.name, !brainzPlayerDisabled);
  const sentryCreateBrowserRouter = Sentry.wrapCreateBrowserRouter(
    createBrowserRouter
  );
  const router = sentryCreateBrowserRouter(routes);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <Helmet defaultTitle="ListenBrainz" titleTemplate="%s - ListenBrainz" />
        <ReactQueryDevtool client={queryClient}>
          {brainzPlayerDisabled ? (
            <RouterProvider router={router} />
          ) : (
            <BrainzPlayerProvider>
              <RouterProvider router={router} />
            </BrainzPlayerProvider>
          )}
        </ReactQueryDevtool>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
