/* eslint-disable no-console */
import * as React from "react";
import * as ReactDOM from "react-dom";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { io } from "socket.io-client";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";

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

  if (!currentUser) {
    return (
      <div>
        Please{" "}
        <a href="https://listenbrainz.org/login/">log in to ListenBrainz</a>
      </div>
    );
  }

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
        props.newAlert(
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
            props.newAlert(
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

  return (
    <MetadataViewer recordingData={recordingData} playingNow={currentListen} />
  );
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
  const { playing_now } = reactProps;

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
          playingNow={playing_now}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
