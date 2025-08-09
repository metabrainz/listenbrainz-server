import * as React from "react";
import { useAtomValue, useSetAtom, useStore } from "jotai";
import { assign, cloneDeep, omit } from "lodash";
import {
  currentListenAtom,
  currentDataSourceIndexAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  currentTrackAlbumAtom,
  currentTrackURLAtom,
  durationMsAtom,
  listenSubmittedAtom,
} from "../BrainzPlayerAtoms";
import { DataSourceTypes } from "../BrainzPlayer";

interface ListenSubmissionProps {
  currentUser: ListenBrainzUser;
  listenBrainzAPIBaseURI: string;
  onError: (error: any, title: string) => void;
  onWarning: (message: string, title: string) => void;
  dataSourceRefs: React.RefObject<DataSourceTypes>[];
}

/**
 * This hook is used to handle listen submission to ListenBrainz.
 * It is used to get the listen metadata to submit and submit it to ListenBrainz and also to submit the current listen and the now playing listen.
 */
const useListenSubmission = ({
  currentUser,
  listenBrainzAPIBaseURI,
  onError,
  onWarning,
  dataSourceRefs,
}: ListenSubmissionProps) => {
  const store = useStore();

  // Atom values
  const currentListen = useAtomValue(currentListenAtom);
  const durationMs = useAtomValue(durationMsAtom);

  // Atom setters
  const setListenSubmitted = useSetAtom(listenSubmittedAtom);

  // Store getters
  const getCurrentDataSourceIndex = () => store.get(currentDataSourceIndexAtom);
  const getCurrentTrackName = () => store.get(currentTrackNameAtom);
  const getCurrentTrackArtist = () => store.get(currentTrackArtistAtom);
  const getCurrentTrackAlbum = () => store.get(currentTrackAlbumAtom);
  const getCurrentTrackURL = () => store.get(currentTrackURLAtom);

  const getListenMetadataToSubmit = React.useCallback((): BaseListenFormat => {
    const dataSource = dataSourceRefs[getCurrentDataSourceIndex()];

    const brainzplayer_metadata = {
      artist_name: getCurrentTrackArtist(),
      release_name: getCurrentTrackAlbum(),
      track_name: getCurrentTrackName(),
    };

    // Create a new listen and augment it with the existing listen and datasource's metadata
    const newListen: BaseListenFormat = {
      // convert Javascript millisecond time to unix epoch in seconds
      listened_at: Math.floor(Date.now() / 1000),
      track_metadata:
        cloneDeep((currentListen as BaseListenFormat)?.track_metadata) ?? {},
    };

    const musicServiceName = dataSource?.current?.name;
    let musicServiceDomain = dataSource?.current?.domainName;

    // Best effort try to get domain from URL
    const currentTrackURL = getCurrentTrackURL();
    if (!musicServiceDomain && currentTrackURL) {
      try {
        musicServiceDomain = new URL(currentTrackURL).hostname;
      } catch (e) {
        // Fallback gracefully
      }
    }

    // Ensure the track_metadata.additional_info path exists and add brainzplayer_metadata field
    assign(newListen.track_metadata, {
      brainzplayer_metadata,
      additional_info: {
        duration_ms: durationMs > 0 ? durationMs : undefined,
        media_player: "BrainzPlayer",
        submission_client: "BrainzPlayer",
        // TODO:  passs the GIT_COMMIT_SHA env variable to the globalprops and add it here as submission_client_version
        // submission_client_version:"",
        music_service: musicServiceDomain,
        music_service_name: musicServiceName,
        origin_url: currentTrackURL,
      },
    });

    return newListen;
  }, [
    dataSourceRefs,
    getCurrentDataSourceIndex,
    getCurrentTrackArtist,
    getCurrentTrackAlbum,
    getCurrentTrackName,
    getCurrentTrackURL,
    currentListen,
    durationMs,
  ]);

  const submitListenToListenBrainz = React.useCallback(
    async (
      listenType: ListenType,
      listen: BaseListenFormat,
      retries: number = 3
    ): Promise<void> => {
      const dataSource = dataSourceRefs[getCurrentDataSourceIndex()];

      if (!currentUser || !currentUser.auth_token) {
        return;
      }

      const isPlayingNowType = listenType === "playing_now";

      // Always submit playing_now listens for a better experience on LB pages
      // Also submit for services that don't record listens themselves
      if (
        isPlayingNowType ||
        (dataSource?.current && !dataSource.current.datasourceRecordsListens())
      ) {
        try {
          const { auth_token } = currentUser;
          let processedPayload = listen;

          // When submitting playing_now listens, listened_at must NOT be present
          if (isPlayingNowType) {
            processedPayload = omit(listen, "listened_at") as Listen;
          }

          const struct = {
            listen_type: listenType,
            payload: [processedPayload],
          } as SubmitListensPayload;

          const url = `${listenBrainzAPIBaseURI}/submit-listens`;

          const response = await fetch(url, {
            method: "POST",
            headers: {
              Authorization: `Token ${auth_token}`,
              "Content-Type": "application/json;charset=UTF-8",
            },
            body: JSON.stringify(struct),
          });

          if (!response.ok) {
            throw new Error(response.statusText);
          }
        } catch (error) {
          if (retries > 0) {
            // Retry with exponential backoff
            await new Promise((resolve) => {
              setTimeout(resolve, 3000 * (4 - retries)); // 3s, 6s, 9s
            });
            await submitListenToListenBrainz(listenType, listen, retries - 1);
          } else if (!isPlayingNowType) {
            onWarning(
              error instanceof Error ? error.message : error.toString(),
              "Could not save this listen"
            );
          }
        }
      }
    },
    [
      dataSourceRefs,
      getCurrentDataSourceIndex,
      currentUser,
      listenBrainzAPIBaseURI,
      onError,
      onWarning,
    ]
  );

  const submitCurrentListen = React.useCallback(async (): Promise<void> => {
    const listen = getListenMetadataToSubmit();
    setListenSubmitted(true);
    await submitListenToListenBrainz("single", listen);
  }, [
    getListenMetadataToSubmit,
    setListenSubmitted,
    submitListenToListenBrainz,
  ]);

  const submitNowPlaying = React.useCallback(async (): Promise<void> => {
    const listen = getListenMetadataToSubmit();
    return submitListenToListenBrainz("playing_now", listen);
  }, [getListenMetadataToSubmit, submitListenToListenBrainz]);

  return {
    submitListenToListenBrainz,
    submitCurrentListen,
    submitNowPlaying,
  };
};

export default useListenSubmission;
