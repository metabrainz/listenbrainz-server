/* eslint-disable no-console */
import * as React from "react";
import * as ReactDOM from "react-dom";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import MetadataViewer from "./MetadataViewer";

import fakeData from "./fakedata.json";
import fakeData2 from "./fakedata-lookup.json";

export type PlayingNowPageProps = {
  playingNow?: Listen;
  recordingData?: MetadataLookup;
} & WithAlertNotificationsInjectedProps;

export default class PlayingNowPage extends React.Component<
  PlayingNowPageProps
> {
  static contextType = GlobalAppContext;

  render() {
    const { recordingData } = this.props;
    return <MetadataViewer recordingData={recordingData} />;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  // const { playing_now, metadata } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const PlayingNowPageWithAlertNotifications = withAlertNotifications(
    PlayingNowPage
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <PlayingNowPageWithAlertNotifications
          initialAlerts={optionalAlerts}
          //   playingNow={playing_now}
          recordingData={fakeData2}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
