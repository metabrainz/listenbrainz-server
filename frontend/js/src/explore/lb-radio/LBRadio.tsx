/* eslint-disable jsx-a11y/anchor-is-valid */

import NiceModal from "@ebay/nice-modal-react";
import { merge } from "lodash";
import * as React from "react";
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { toast } from "react-toastify";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import Loader from "../../components/Loader";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import { ToastMsg } from "../../notifications/Notifications";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
} from "../../playlists/utils";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import { LBRadioFeedback, Playlist } from "./Playlist";
import Prompt, { Modes } from "./Prompt";

type LBRadioProps = {
  modeArg: Modes;
  promptArg: string;
};

function LBRadio(props: LBRadioProps) {
  const { modeArg, promptArg } = props;
  const [jspfPlaylist, setJspfPlaylist] = React.useState<JSPFObject>();
  const [feedback, setFeedback] = React.useState<string[]>([]);
  const [isLoading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const generatePlaylistCallback = React.useCallback(
    async (prompt: string, mode: Modes) => {
      setErrorMessage("");
      setLoading(true);
      try {
        const request = await fetch(
          `${
            APIService.APIBaseURI
          }/explore/lb-radio?prompt=${encodeURIComponent(prompt)}&mode=${mode}`
        );
        if (request.ok) {
          const body: {
            payload: { jspf: JSPFObject; feedback: string[] };
          } = await request.json();
          const { payload } = body;
          const { playlist } = payload?.jspf as JSPFObject;
          if (playlist?.track?.length) {
            // Augment track with metadata fetched from LB server, mainly so we can have cover art
            try {
              const recordingMetadataMap = await APIService.getRecordingMetadata(
                playlist.track.map(getRecordingMBIDFromJSPFTrack)
              );
              if (recordingMetadataMap) {
                playlist?.track.forEach((track) => {
                  const mbid = getRecordingMBIDFromJSPFTrack(track);
                  if (recordingMetadataMap[mbid]) {
                    // This object MUST follow the JSPFTrack type.
                    // We don't set the correct ype here because we have an incomplete object
                    const newTrackObject = {
                      duration: recordingMetadataMap[mbid].recording?.length,
                      extension: {
                        [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: {
                          additional_metadata: {
                            caa_id: recordingMetadataMap[mbid].release?.caa_id,
                            caa_release_mbid:
                              recordingMetadataMap[mbid].release
                                ?.caa_release_mbid,
                          },
                        },
                      },
                    };
                    // Merge the existing track and our extra metadata object
                    merge(track, newTrackObject);
                  }
                });
              }
            } catch (error) {
              // Don't do anything about this error, it's just metadata augmentation
              // eslint-disable-next-line no-console
              setErrorMessage(error);
              setJspfPlaylist(undefined);
              setFeedback([]);
            }
          }
          setJspfPlaylist(payload.jspf);
          setFeedback(payload.feedback);
        } else {
          const msg = await request.json();
          setErrorMessage(msg?.error);
          setJspfPlaylist(undefined);
          setFeedback([]);
        }
      } catch (error) {
        setErrorMessage(error);
      }
      setLoading(false);
    },
    [setJspfPlaylist, setFeedback, APIService]
  );

  const onSavePlaylist = React.useCallback(async () => {
    // TODO: Move the guts of this to APIService
    const args = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${currentUser.auth_token}`,
      },
      body: JSON.stringify(jspfPlaylist),
    };
    try {
      const request = await fetch(
        `${APIService.APIBaseURI}/playlist/create`,
        args
      );
      if (request.ok) {
        const { playlist_mbid } = await request.json();
        toast.success(
          <ToastMsg
            title="Saved playlist"
            message={
              <>
                Playlist saved to &ensp;
                <a href={`/playlist/${playlist_mbid}`}>
                  {jspfPlaylist?.playlist.title}
                </a>
              </>
            }
          />,
          { toastId: "saved-playlist" }
        );
      } else {
        const { error } = await request.json();
        toast.error(
          <ToastMsg
            title="Error"
            message={`Failed to save playlist: ${error}.`}
          />,
          { toastId: "saved-playlist-error" }
        );
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to save playlist: ${error}.`}
        />,
        { toastId: "saved-playlist-error" }
      );
    }
  }, [currentUser.auth_token, jspfPlaylist, APIService.APIBaseURI]);

  return (
    <>
      <div className="row">
        <div className="col-sm-12">
          <Prompt
            onGenerate={generatePlaylistCallback}
            errorMessage={errorMessage}
            initPrompt={promptArg}
            initMode={modeArg}
          />
          <Loader
            isLoading={isLoading}
            loaderText="Generating playlist…"
            className="playlist-loader"
          >
            <LBRadioFeedback feedback={feedback} />
            <Playlist
              playlist={jspfPlaylist?.playlist}
              onSavePlaylist={onSavePlaylist}
            />
          </Loader>
        </div>
      </div>
      <BrainzPlayer
        listens={jspfPlaylist?.playlist?.track?.map(JSPFTrackToListen) ?? []}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalAppContext } = getPageProps();

  const { user, mode, prompt, token } = reactProps;
  const renderRoot = createRoot(domContainer!);
  const LBRadioWithAlertNotifications = withAlertNotifications(LBRadio);

  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <LBRadioWithAlertNotifications modeArg={mode} promptArg={prompt} />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
