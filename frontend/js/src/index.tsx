import * as React from "react";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Helmet } from "react-helmet";
import ErrorBoundary from "./utils/ErrorBoundary";
import GlobalAppContext from "./utils/GlobalAppContext";
import { getPageProps } from "./utils/utils";
import getRoutes from "./routes/routes";
import queryClient from "./utils/QueryClient";
import ReactQueryDevtool from "./utils/ReactQueryDevTools";

document.addEventListener("DOMContentLoaded", async () => {
  const { domContainer, globalAppContext, sentryProps } = await getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { currentUser } = globalAppContext;

  const routes = getRoutes(currentUser?.name);
  const router = createBrowserRouter(routes);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <Helmet defaultTitle="ListenBrainz" titleTemplate="%s - ListenBrainz">
          <meta property="og:type" content="website" />
          <meta
            property="og:image"
            content="https://listenbrainz.org/static/img/share-header.png"
          />
          <meta property="og:image:width" content="1280" />
          <meta property="og:image:height" content="640" />

          <meta name="twitter:card" content="summary_large_image" />
          <meta property="twitter:domain" content="listenbrainz.org" />
          <meta name="twitter:title" content="ListenBrainz" />
          <meta
            name="twitter:image"
            content="https://listenbrainz.org/static/img/share-header.png"
          />
        </Helmet>
        <ReactQueryDevtool client={queryClient}>
          <RouterProvider router={router} />
        </ReactQueryDevtool>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
