/* eslint-disable no-console */
import * as React from "react";
import { toast } from "react-toastify";
import { io } from "socket.io-client";
import { Link, useLoaderData } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";

import MetadataViewer from "./components/MetadataViewer";
import { ToastMsg } from "../notifications/Notifications";

export type PlayingNowPageProps = {
  playingNow?: Listen;
};

export default function PlayingNowPage(props: PlayingNowPageProps) {
  const { playingNow } = props;
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
        toast.error(
          <ToastMsg
            title="Could not load currently playing track"
            message={error.message}
          />,
          { toastId: "load-playback-error" }
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
        toast.error(<ToastMsg title="Something went wrong" message={error} />, {
          toastId: "error",
        });
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
            toast.error(
              <ToastMsg
                title="Error fetching your currently playing track"
                message={error.message ?? error}
              />,
              { toastId: "playing-now-error" }
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
        Please <Link to="/login/">log in to ListenBrainz</Link>
      </div>
    );
  }

  return (
    <MetadataViewer recordingData={recordingData} playingNow={currentListen} />
  );
}

export function PlayingNowPageWrapper() {
  const { playingNow } = useLoaderData() as PlayingNowPageProps;
  return <PlayingNowPage playingNow={playingNow} />;
}
