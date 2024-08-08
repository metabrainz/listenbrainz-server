/* eslint-disable jsx-a11y/anchor-is-valid */

import { merge } from "lodash";
import * as React from "react";
import { useState } from "react";
import { useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import Loader from "../../components/Loader";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
} from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { LBRadioFeedback, Playlist } from "./components/Playlist";
import Prompt, { Modes } from "./components/Prompt";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

type LBRadioLoaderData = {
  mode: Modes;
  prompt: string;
};

export default function LBRadio() {
  const data = useLoaderData() as LBRadioLoaderData;
  const { mode: modeArg, prompt: promptArg } = data;

  const [jspfPlaylist, setJspfPlaylist] = React.useState<JSPFObject>();
  const [feedback, setFeedback] = React.useState<string[]>([]);
  const [isLoading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const { APIService } = React.useContext(GlobalAppContext);
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
                            artists: recordingMetadataMap[
                              mbid
                            ].artist?.artists?.map((a) => {
                              return {
                                artist_credit_name: a.name,
                                artist_mbid: a.artist_mbid,
                                join_phrase: a.join_phrase || "",
                              };
                            }),
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

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: jspfPlaylist?.playlist?.track?.map(JSPFTrackToListen),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jspfPlaylist?.playlist?.track]);

  return (
    <div role="main">
      <Helmet>
        <title>LB Radio</title>
      </Helmet>
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
            <Playlist playlist={jspfPlaylist?.playlist} />
          </Loader>
        </div>
      </div>
    </div>
  );
}
