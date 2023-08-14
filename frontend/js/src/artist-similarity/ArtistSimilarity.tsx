import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { ErrorBoundary } from "@sentry/react";
import Data from "./Data";
import { getPageProps } from "../utils/utils";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";

function ArtistSimilarity() {
  return <Data />;
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalAppContext, sentryProps } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const ArtistSimilarityPageWithAlertNotifications = withAlertNotifications(
    ArtistSimilarity
  );

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <ArtistSimilarityPageWithAlertNotifications />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
