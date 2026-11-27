/* eslint-disable jsx-a11y/anchor-is-valid */

import { merge } from "lodash";
import * as React from "react";
import { useState } from "react";
import { useLoaderData } from "react-router";
import { Helmet } from "react-helmet";
import { useSetAtom } from "jotai";
import Loader from "../../components/Loader";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
} from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { LBRadioFeedback, Playlist } from "./components/Playlist";
import Prompt, { Modes } from "./components/Prompt";
import {
  ambientQueueAtom,
  setAmbientQueueAtom,
} from "../../common/brainzplayer/BrainzPlayerAtoms";

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

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const generatePlaylistCallback = React.useCallback(
    async (prompt: string, mode: Modes) => {
      if (!currentUser?.auth_token) {
        setErrorMessage(
          "Please log in to use LB Radio. (AI scrapers ruin everything!)"
        );
        return;
      }
      setErrorMessage("");
      setLoading(true);
      try {
        const { payload } = await APIService.getLBRadioPlaylist(
          currentUser.auth_token,
          prompt,
          mode
        );
        const { playlist } = payload?.jspf as JSPFObject;
        if (playlist?.track?.length) {
          // Augment track with metadata fetched from LB server, mainly so we can have cover art
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
                          recordingMetadataMap[mbid].release?.caa_release_mbid,
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
        }
        // The sortable list needs a unique id on each track, and the same
        // recording can appear more than once so the MBID is not enough
        payload.jspf?.playlist?.track?.forEach((track: JSPFTrack, index) => {
          // eslint-disable-next-line no-param-reassign
          track.id = `${getRecordingMBIDFromJSPFTrack(track)}-${index}`;
        });
        setJspfPlaylist(payload.jspf);
        setFeedback(payload.feedback);
      } catch (error) {
        setErrorMessage(error);
        setJspfPlaylist(undefined);
        setFeedback([]);
      }
      setLoading(false);
    },
    [setJspfPlaylist, setFeedback, APIService, currentUser]
  );

  const removeTrack = React.useCallback((trackToRemove: JSPFTrack) => {
    setJspfPlaylist((prevJspf) => {
      if (!prevJspf?.playlist?.track) {
        return prevJspf;
      }
      return {
        ...prevJspf,
        playlist: {
          ...prevJspf.playlist,
          // Compare by reference: the same recording can appear more than once
          track: prevJspf.playlist.track.filter(
            (track) => track !== trackToRemove
          ),
        },
      };
    });
  }, []);

  const reorderTracks = React.useCallback((reorderedTracks: JSPFTrack[]) => {
    setJspfPlaylist((prevJspf) => {
      if (!prevJspf?.playlist) {
        return prevJspf;
      }
      return {
        ...prevJspf,
        playlist: { ...prevJspf.playlist, track: reorderedTracks },
      };
    });
  }, []);

  const setAmbientQueue = useSetAtom(setAmbientQueueAtom);
  const replaceAmbientQueue = useSetAtom(ambientQueueAtom);

  React.useEffect(() => {
    const tracks = jspfPlaylist?.playlist?.track;
    if (tracks && tracks.length === 0) {
      // setAmbientQueue ignores empty lists, which would leave the tracks
      // of a now empty playlist playable (after removing the last one)
      replaceAmbientQueue([]);
      return;
    }
    setAmbientQueue(tracks?.map(JSPFTrackToListen) ?? []);
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
            <Playlist
              playlist={jspfPlaylist?.playlist}
              onRemoveTrack={removeTrack}
              onReorderTracks={reorderTracks}
            />
          </Loader>
        </div>
      </div>
    </div>
  );
}
