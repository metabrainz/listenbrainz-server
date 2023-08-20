import React, {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useRef,
} from "react";
import { throttle, throttle as _throttle } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import GlobalAppContext from "./GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

const RECORDING_MBID_REGEXP = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;
type SearchTrackOrMBIDProps = {
  onSelectRecording: (selectedRecordingMetadata: TrackMetadata) => void;
};

export default function SearchTrackOrMBID({
  onSelectRecording,
}: SearchTrackOrMBIDProps) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBRecording } = APIService;
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState("");
  const [searchResults, setSearchResults] = useState<Array<ACRMSearchResult>>(
    []
  );

  useEffect(() => {
    // autoFocus property on the input element does not work
    // We need to wait for the modal animated transition to finish
    // and trigger the focus manually.
    setTimeout(() => {
      inputRef?.current?.focus();
    }, 600);
  }, []);

  const handleError = useCallback(
    (error: string | Error, title?: string): void => {
      if (!error) {
        return;
      }
      toast.error(
        <ToastMsg
          title={title || "Error"}
          message={typeof error === "object" ? error.message : error}
        />,
        { toastId: "search-error" }
      );
    },
    []
  );

  const throttledSearchTrack = useMemo(
    () =>
      throttle(
        async (searchString: string) => {
          try {
            const response = await fetch(
              "https://labs.api.listenbrainz.org/recording-search/json",
              {
                method: "POST",
                body: JSON.stringify([{ query: searchString }]),
                headers: {
                  "Content-type": "application/json; charset=UTF-8",
                },
              }
            );

            const parsedResponse = await response.json();
            setSearchResults(parsedResponse);
          } catch (error) {
            handleError(error);
          }
        },
        800,
        { leading: false, trailing: true }
      ),
    [handleError, setSearchResults]
  );

  const throttledHandleValidMBID = useMemo(
    () =>
      throttle(
        async (input: string) => {
          const newRecordingMBID = RECORDING_MBID_REGEXP.exec(
            input
          )![2].toLowerCase();

          try {
            const recordingLookupResponse = (await lookupMBRecording(
              newRecordingMBID,
              "artists+releases"
            )) as MusicBrainzRecordingWithReleases;

            const newMetadata: TrackMetadata = {
              track_name: recordingLookupResponse.title,
              artist_name: recordingLookupResponse["artist-credit"]
                .map((ac) => ac.name + ac.joinphrase)
                .join(""),
              additional_info: {
                duration_ms: recordingLookupResponse.length,
                artist_mbids: recordingLookupResponse["artist-credit"].map(
                  (ac) => ac.artist.id
                ),
                release_artist_names: recordingLookupResponse[
                  "artist-credit"
                ].map((ac) => ac.artist.name),
                recording_mbid: recordingLookupResponse.id,
                release_mbid: recordingLookupResponse.releases[0]?.id,
              },
            };
            onSelectRecording(newMetadata);
          } catch (error) {
            handleError(
              `We could not find a recording on MusicBrainz with the MBID ${newRecordingMBID} ('${error.message}')`,
              "Could not find recording"
            );
            setInputValue("");
          }
          setSearchResults([]);
        },
        800,
        { leading: false, trailing: true }
      ),
    [lookupMBRecording, handleError, onSelectRecording]
  );

  const selectSearchResult = (track: ACRMSearchResult) => {
    const metadata: TrackMetadata = {
      additional_info: {
        release_mbid: track.release_mbid,
        recording_mbid: track.recording_mbid,
      },

      artist_name: track.artist_credit_name,
      track_name: track.recording_name,
      release_name: track.release_name,
    };
    onSelectRecording(metadata);
  };

  const reset = () => {
    setInputValue("");
    setSearchResults([]);
  };

  useEffect(() => {
    if (!inputValue) {
      return;
    }
    const isValidUUID = RECORDING_MBID_REGEXP.test(inputValue);
    if (isValidUUID) {
      throttledHandleValidMBID(inputValue);
    } else {
      throttledSearchTrack(inputValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputValue]);

  return (
    <div>
      <div className="input-group track-search">
        <input
          type="search"
          value={inputValue}
          className="form-control"
          id="recording-mbid"
          name="recording-mbid"
          onChange={(event) => {
            setInputValue(event.target.value);
          }}
          placeholder="Track name or MusicBrainz URL/MBID"
          required
          ref={inputRef}
        />
        <span className="input-group-btn">
          <button className="btn btn-default" type="button" onClick={reset}>
            <FontAwesomeIcon icon={faTimesCircle} />
          </button>
        </span>
        {Boolean(searchResults?.length) && (
          <div className="track-search-dropdown">
            {searchResults.map((track) => {
              return (
                <button
                  key={track.recording_mbid}
                  type="button"
                  onClick={() => selectSearchResult(track)}
                >
                  {`${track.recording_name} - ${track.artist_credit_name}`}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
