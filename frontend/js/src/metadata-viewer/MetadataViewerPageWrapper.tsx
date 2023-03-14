/* eslint-disable no-console */
import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { io } from "socket.io-client";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";
import MetadataViewer from "./MetadataViewer";

export type PlayingNowPageProps = {
  playingNow?: Listen;
} & WithAlertNotificationsInjectedProps;

export default function PlayingNowPage(props: PlayingNowPageProps) {
  const { playingNow, newAlert } = props;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [currentListen, setCurrentListen] = React.useState(playingNow);
  const [recordingData, setRecordingData] = React.useState<MetadataLookup>();

  /** Metadata lookup and storage */
  const onNewPlayingNow = React.useCallback(
    async (playingNowListen: Listen) => {
      setCurrentListen(playingNowListen);
      try {
        const metadata = await APIService.lookupRecordingMetadata(
          playingNowListen.track_metadata.track_name,
          playingNowListen.track_metadata.artist_name
        );
        if (metadata) {
          setRecordingData(metadata);
        }
      } catch (error) {
        newAlert(
          "danger",
          "Could not load currently playing track",
          error.message
        );
      }
    },
    [setCurrentListen, setRecordingData]
  );

  /** Websockets connection */
  React.useEffect(() => {
    const socket = io(`${window.location.origin}`, { path: "/socket.io/" });
    socket.on("connect", () => {
      socket.emit("json", { user: currentUser.name });
    });
    socket.on("playing_now", async (data: string) => {
      try {
        const newPlayingNow = JSON.parse(data) as Listen;
        newPlayingNow.playing_now = true;
        await onNewPlayingNow(newPlayingNow);
      } catch (error) {
        newAlert("danger", "Something went wrong", error);
      }
    });
    return () => {
      socket.close();
    };
  }, []);

  /** On page load, hit the API to get the user's most recent playing-now (if any) */
  React.useEffect(() => {
    // Only run this if no playing-now was present in the props on load
    if (!currentListen || !recordingData) {
      const fetchPlayingNow = async () => {
        if (!recordingData && currentUser) {
          try {
            const propOrFetchedPlayingNow =
              currentListen ??
              (await APIService.getPlayingNowForUser(currentUser.name));
            if (propOrFetchedPlayingNow) {
              await onNewPlayingNow(propOrFetchedPlayingNow);
            }
          } catch (error) {
            newAlert(
              "danger",
              "Error fetching your currently playing track",
              error.message ?? error
            );
          }
        }
      };
      fetchPlayingNow();
    }
  }, []);

  if (!currentUser) {
    return (
      <div>
        Please{" "}
        <a href="https://listenbrainz.org/login/">log in to ListenBrainz</a>
      </div>
    );
  }

  return (
    <MetadataViewer recordingData={recordingData} playingNow={currentListen} />
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
    optionalAlerts,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { playing_now } = reactProps;

  const PlayingNowPageWithAlertNotifications = withAlertNotifications(
    PlayingNowPage
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <PlayingNowPageWithAlertNotifications
          initialAlerts={optionalAlerts}
          playingNow={playing_now}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
