import * as React from "react";
import { useAtomValue, useSetAtom, useStore } from "jotai";
import { assign, cloneDeep } from "lodash";
import { useEffect, useMemo } from "react";
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
import {
  saveFailedListen,
  getFailedListens,
  removeFailedListen,
} from "../../../utils/listenStorage";
import APIService from "../../../utils/APIService";

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
  const apiService = useMemo(() => new APIService(listenBrainzAPIBaseURI), [
    listenBrainzAPIBaseURI,
  ]);
  const retryOfflineListens = React.useCallback(async () => {
    if (!navigator.onLine) return;

    const failedListens = await getFailedListens();
    if (failedListens.length === 0) return;

    onWarning(
      `Retrying ${failedListens.length} unsent listens...`,
      "Back Online"
    );

    try {
      if (!currentUser || !currentUser.auth_token) return;
      const payload = failedListens.map((item) => item.listen);
      await apiService.submitListens(currentUser.auth_token, "single", payload);
      await Promise.all(
        failedListens.map((item) => removeFailedListen(item.id))
      );
    } catch (error) {
      onError(error, "Retry Failed");
    }
  }, [currentUser, apiService, onWarning, onError]);
  useEffect(() => {
    window.addEventListener("online", retryOfflineListens);
    retryOfflineListens();
    return () => {
      window.removeEventListener("online", retryOfflineListens);
    };
  }, [retryOfflineListens]);

  // Atom values
  const currentListen = useAtomValue(currentListenAtom);
  const durationMs = useAtomValue(durationMsAtom);

  // Atom setters
  const setListenSubmitted = useSetAtom(listenSubmittedAtom);

  // Store getters
  const getCurrentDataSourceIndex = React.useCallback(
    () => store.get(currentDataSourceIndexAtom),
    [store]
  );

  const getListenMetadataToSubmit = React.useCallback((): BaseListenFormat => {
    const dataSource = dataSourceRefs[getCurrentDataSourceIndex()];

    const brainzplayer_metadata = {
      artist_name: store.get(currentTrackArtistAtom),
      release_name: store.get(currentTrackAlbumAtom),
      track_name: store.get(currentTrackNameAtom),
    };

    // Create a new listen and augment it with the existing listen and datasource's metadata
    const newListen: BaseListenFormat = {
      // convert Javascript millisecond time to unix epoch in seconds
      listened_at: Math.floor(Date.now() / 1000),
      track_metadata:
        cloneDeep((currentListen as BaseListenFormat)?.track_metadata) ?? {},
    };

    // In some edge cases (eg. playing from stats page), listen metadata does not contain a track/artist name.
    // The absence of track_name results in a rejected listen submission, so ensure there is one.
    if (
      !newListen.track_metadata.track_name &&
      brainzplayer_metadata.track_name
    ) {
      newListen.track_metadata.track_name =
        newListen.track_metadata.track_name || brainzplayer_metadata.track_name;
    }
    if (
      !newListen.track_metadata.artist_name &&
      brainzplayer_metadata.artist_name
    ) {
      newListen.track_metadata.artist_name = brainzplayer_metadata.artist_name;
    }
    if (newListen.track_metadata.release_name === "") {
      delete newListen.track_metadata.release_name;
    }

    const musicServiceName = dataSource?.current?.name;
    let musicServiceDomain = dataSource?.current?.domainName;

    // Best effort try to get domain from URL
    const currentTrackURL = store.get(currentTrackURLAtom);
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
    store,
    currentListen,
    durationMs,
  ]);

  const submitListenToListenBrainz = React.useCallback(
    async (listenType: ListenType, listen: BaseListenFormat): Promise<void> => {
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
          await apiService.submitListens(currentUser.auth_token, listenType, [
            listen,
          ]);
        } catch (error) {
          if (!isPlayingNowType) {
            await saveFailedListen(listen as Listen);
            onWarning(
              "Connection lost. Listen saved locally.",
              "Submission Failed"
            );
          }
        }
      }
    },
    [
      dataSourceRefs,
      getCurrentDataSourceIndex,
      currentUser,
      apiService,
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
