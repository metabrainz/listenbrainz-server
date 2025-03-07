import { faSpinner, faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { isFunction, throttle } from "lodash";
import React, {
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "./GlobalAppContext";
import DropdownRef from "./Dropdown";
import {
  LB_ALBUM_MBID_REGEXP,
  RECORDING_MBID_REGEXP,
  RELEASE_GROUP_MBID_REGEXP,
  RELEASE_MBID_REGEXP,
  UUID_REGEXP,
} from "./constants";

const THROTTLE_MILLISECONDS = 1500;

type PayloadType = "trackmetadata" | "recording";
// Allow for returning results of two different types while maintaining
// type safety, depending on the value of expectedPayload
type ConditionalReturnValue =
  | {
      onSelectRecording: (
        selectedRecording: MusicBrainzRecordingWithReleasesAndRGs
      ) => void;
      expectedPayload: "recording";
    }
  | {
      onSelectRecording: (selectedRecording: TrackMetadata) => void;
      expectedPayload: "trackmetadata";
    };

type SearchTrackOrMBIDProps = {
  autofocus?: boolean;
  defaultValue?: string;
  expectedPayload: PayloadType;
  switchMode?: (text: string) => void;
} & ConditionalReturnValue;

const SearchTrackOrMBID = forwardRef(function SearchTrackOrMBID(
  {
    onSelectRecording,
    expectedPayload,
    defaultValue,
    autofocus = true,
    switchMode,
  }: SearchTrackOrMBIDProps,
  inputRefForParent
) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBRecording } = APIService;
  const dropdownRef = DropdownRef();
  const [inputValue, setInputValue] = useState(defaultValue ?? "");
  const [searchResults, setSearchResults] = useState<Array<ACRMSearchResult>>(
    []
  );
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRefLocal = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  // Allow parents to focus on input
  useImperativeHandle(
    inputRefForParent,
    () => {
      return {
        focus() {
          inputRefLocal?.current?.focus();
        },
        triggerSearch(newText: string) {
          setInputValue(newText);
        },
      };
    },
    []
  );

  // Autofocus once on load
  useEffect(() => {
    if (autofocus) {
      setTimeout(() => {
        inputRefLocal?.current?.focus();
      }, 500);
    }
  }, [autofocus]);

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
          } finally {
            setLoading(false);
          }
        },
        THROTTLE_MILLISECONDS,
        { leading: false, trailing: true }
      ),
    [handleError, setSearchResults]
  );

  const throttledHandleValidMBID = useMemo(
    () =>
      throttle(
        async (input: string, canonicalReleaseMBID?: string) => {
          let newRecordingMBID =
            RECORDING_MBID_REGEXP.exec(input)?.[1] ??
            UUID_REGEXP.exec(input)?.[0];
          if (!newRecordingMBID) {
            return;
          }
          newRecordingMBID = newRecordingMBID?.toLowerCase();
          try {
            const recordingLookupResponse = (await lookupMBRecording(
              newRecordingMBID,
              "artists+releases+release-groups"
            )) as MusicBrainzRecordingWithReleasesAndRGs;

            const canonicalReleaseIndex = recordingLookupResponse.releases.findIndex(
              (r) => r.id === canonicalReleaseMBID
            );
            if (canonicalReleaseIndex !== -1) {
              // sort the canonical release as #1, for use in
              const canonicalRelease = recordingLookupResponse.releases.splice(
                canonicalReleaseIndex,
                1
              );
              recordingLookupResponse.releases.unshift(canonicalRelease[0]);
            }
            if (expectedPayload === "recording") {
              onSelectRecording(recordingLookupResponse);
            } else {
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
            }
          } catch (error) {
            handleError(
              `We could not find a recording on MusicBrainz with the MBID ${newRecordingMBID} ('${error.message}')`,
              "Could not find recording"
            );
            setInputValue("");
          } finally {
            setLoading(false);
          }
          setSearchResults([]);
        },
        THROTTLE_MILLISECONDS,
        { leading: false, trailing: true }
      ),
    [lookupMBRecording, expectedPayload, onSelectRecording, handleError]
  );

  const selectSearchResult = (track: ACRMSearchResult) => {
    if (expectedPayload === "recording") {
      // Expecting a recording, fetch it so we can return it
      throttledHandleValidMBID(track.recording_mbid, track.release_mbid);
    } else {
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
    }
  };

  const reset = () => {
    setInputValue("");
    setSearchResults([]);
    setSelectedIndex(-1);
    inputRefLocal?.current?.focus();
  };

  useEffect(() => {
    if (!inputValue) {
      return;
    }
    setLoading(true);
    const isValidUUID = UUID_REGEXP.test(inputValue);
    const isValidRecordingUUID = RECORDING_MBID_REGEXP.test(inputValue);
    const isValidAlbumUUID =
      RELEASE_MBID_REGEXP.test(inputValue) ||
      RELEASE_GROUP_MBID_REGEXP.test(inputValue) ||
      LB_ALBUM_MBID_REGEXP.test(inputValue);
    if (isValidAlbumUUID && isFunction(switchMode)) {
      switchMode(inputValue);
      return;
    }
    if (isValidUUID || isValidRecordingUUID) {
      throttledHandleValidMBID(inputValue);
    } else {
      throttledSearchTrack(inputValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputValue]);

  return (
    <div>
      <div className="input-group dropdown-search" ref={dropdownRef}>
        <input
          ref={inputRefLocal}
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
        />
        <span className="input-group-btn">
          <button className="btn btn-default" type="button" onClick={reset}>
            {loading ? (
              <FontAwesomeIcon icon={faSpinner} spin />
            ) : (
              <FontAwesomeIcon icon={faTimesCircle} />
            )}
          </button>
        </span>
        {Boolean(searchResults?.length) && (
          <select
            className="dropdown-search-suggestions"
            size={Math.min(searchResults.length + 1, 8)}
            onChange={(e) => {
              if (!e.currentTarget.value) {
                // clicked on "no more options"
                return;
              }
              e.target.blur();
              const selectedTrack = searchResults.find(
                (track) => track.recording_mbid === e.target.value
              );
              selectSearchResult(selectedTrack!);
              reset();
            }}
            tabIndex={-1}
          >
            {searchResults.map((track, index) => {
              const trackNameAndArtistName = `${track.recording_name} - ${track.artist_credit_name}`;
              return (
                <option
                  key={track.recording_mbid}
                  value={track.recording_mbid}
                  style={
                    index === selectedIndex
                      ? { backgroundColor: "#353070", color: "white" }
                      : {}
                  }
                  aria-selected={index === selectedIndex}
                  title={trackNameAndArtistName}
                >
                  {trackNameAndArtistName}
                </option>
              );
            })}
            {searchResults.length < 10 && (
              <option value="" style={{ textAlign: "center", color: "gray" }}>
                — No more options —
              </option>
            )}
          </select>
        )}
      </div>
    </div>
  );
});

export default SearchTrackOrMBID;
