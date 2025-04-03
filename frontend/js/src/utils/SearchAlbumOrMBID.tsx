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
  RELEASE_GROUP_MBID_REGEXP,
  RELEASE_MBID_REGEXP,
  RECORDING_MBID_REGEXP,
  UUID_REGEXP,
} from "./constants";

const THROTTLE_MILLISECONDS = 1500;

type SearchTrackOrMBIDProps = {
  onSelectAlbum: (releaseMBID?: string) => void;
  defaultValue?: string;
  switchMode?: (text: string) => void;
};

const SearchAlbumOrMBID = forwardRef(function SearchAlbumOrMBID(
  { onSelectAlbum, defaultValue, switchMode }: SearchTrackOrMBIDProps,
  inputRefForParent
) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBReleaseGroup, searchMBRelease } = APIService;
  const dropdownRef = DropdownRef();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState(defaultValue ?? "");
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<
    Array<MusicBrainzRelease & Partial<WithMedia> & WithArtistCredits>
  >([]);

  // Allow parents to focus on input and trigger search
  useImperativeHandle(
    inputRefForParent,
    () => {
      return {
        focus() {
          searchInputRef?.current?.focus();
        },
        triggerSearch(newText: string) {
          setInputValue(newText);
        },
      };
    },
    []
  );

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

  const throttledSearchRelease = useMemo(
    () =>
      throttle(
        async (searchString: string) => {
          try {
            const { releases } = await searchMBRelease(searchString);
            setSearchResults(releases);
          } catch (error) {
            handleError(error);
          } finally {
            setLoading(false);
          }
        },
        THROTTLE_MILLISECONDS,
        { leading: false, trailing: true }
      ),
    [handleError, searchMBRelease]
  );

  const throttledHandleValidMBID = useMemo(
    () =>
      throttle(
        async (input: string) => {
          const newReleaseMBID =
            RELEASE_MBID_REGEXP.exec(input)?.[1] ??
            UUID_REGEXP.exec(input)?.[0];
          const newReleaseGroupMBID =
            RELEASE_GROUP_MBID_REGEXP.exec(input)?.[1].toLowerCase() ??
            LB_ALBUM_MBID_REGEXP.exec(input)?.[1].toLowerCase();
          try {
            if (newReleaseMBID) {
              onSelectAlbum(newReleaseMBID);
              setSearchResults([]);
            } else if (newReleaseGroupMBID) {
              const lookupResponse = await lookupMBReleaseGroup(
                newReleaseGroupMBID
              );
              const releasesWithAC = lookupResponse?.releases.map(
                (release) => ({
                  ...release,
                  "artist-credit": lookupResponse["artist-credit"],
                })
              );
              setSearchResults(releasesWithAC);
            } else {
              return;
            }
          } catch (error) {
            handleError(
              `We could not find a release or release-group on MusicBrainz with the MBID ${newReleaseMBID} ('${error.message}')`,
              "Could not find album"
            );
            setInputValue("");
          } finally {
            setLoading(false);
          }
        },
        THROTTLE_MILLISECONDS,
        { leading: false, trailing: true }
      ),
    [lookupMBReleaseGroup, handleError, onSelectAlbum]
  );

  const selectSearchResult = useCallback(
    (releaseId: string) => {
      onSelectAlbum(releaseId);
    },
    [onSelectAlbum]
  );

  const reset = () => {
    setInputValue("");
    setSearchResults([]);
    onSelectAlbum();
    setLoading(false);
    searchInputRef?.current?.focus();
  };

  useEffect(() => {
    if (!inputValue) {
      return;
    }
    setLoading(true);
    const isValidUUID = UUID_REGEXP.test(inputValue);
    const isValidAlbumUUID =
      RELEASE_MBID_REGEXP.test(inputValue) ||
      RELEASE_GROUP_MBID_REGEXP.test(inputValue) ||
      LB_ALBUM_MBID_REGEXP.test(inputValue);
    const isValidRecordingUUID = RECORDING_MBID_REGEXP.test(inputValue);
    if (isValidRecordingUUID && isFunction(switchMode)) {
      switchMode(inputValue);
      return;
    }
    if (isValidUUID || isValidAlbumUUID) {
      throttledHandleValidMBID(inputValue);
    } else {
      throttledSearchRelease(inputValue);
    }
  }, [
    inputValue,
    throttledHandleValidMBID,
    throttledSearchRelease,
    switchMode,
  ]);

  // Autofocus once on load
  useEffect(() => {
    setTimeout(() => {
      searchInputRef?.current?.focus();
    }, 500);
  }, []);

  return (
    <div>
      <div className="input-group dropdown-search" ref={dropdownRef}>
        <input
          ref={searchInputRef}
          type="search"
          value={inputValue}
          className="form-control"
          id="release-mbid"
          name="release-mbid"
          onChange={(event) => {
            setInputValue(event.target.value);
          }}
          placeholder="Album name or MusicBrainz URL/MBID"
          required
          aria-haspopup={Boolean(searchResults?.length)}
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
            onChange={(e) => {
              if (!e.currentTarget.value) {
                // clicked on "no more options"
                return;
              }
              selectSearchResult(e.currentTarget.value);
              e.target.blur();
            }}
            size={Math.min(searchResults.length + 1, 8)}
            tabIndex={-1}
          >
            {searchResults.map((release, index) => {
              let releaseInfoString = `(${release.media
                ?.map((medium) => medium.format)
                .join(" + ")}) 
                ${
                  release.country === "XE" ? "Worldwide" : release.country ?? ""
                } ${release.date ?? ""}`;
              if (release["label-info"]?.length) {
                const labelNames = release["label-info"]
                  ?.map((li) => li.label?.name)
                  .filter(Boolean)
                  .join(", ");
                releaseInfoString += ` - ${labelNames}`;
              }
              const releaseTitleAndArtist = `${release.title} ${
                release.disambiguation ? `(${release.disambiguation})` : ""
              }
- ${
                release["artist-credit"] &&
                release["artist-credit"]
                  .map(
                    (artist) =>
                      `${artist.name} ${
                        artist.joinphrase ? artist.joinphrase : ""
                      }`
                  )
                  .join("")
              }`;
              return (
                <option
                  key={release.id}
                  value={release.id}
                  data-release-info={releaseInfoString}
                  title={releaseTitleAndArtist}
                >
                  {releaseTitleAndArtist}
                </option>
              );
            })}
            {searchResults.length < 25 && (
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

export default SearchAlbumOrMBID;
