import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import React, {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "./GlobalAppContext";

const RELEASE_MBID_REGEXP = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/release\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;
const RELEASE_GROUP_MBID_REGEXP = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/release-group\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;
const THROTTLE_MILLISECONDS = 1500;

type SearchTrackOrMBIDProps = {
  onSelectAlbum: (releaseMBID?: string) => void;
  defaultValue?: string;
};

export default function SearchAlbumOrMBID({
  onSelectAlbum,
  defaultValue,
}: SearchTrackOrMBIDProps) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBReleaseGroup, searchMBRelease } = APIService;
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = React.useRef<HTMLSelectElement>(null);
  const [inputValue, setInputValue] = useState(defaultValue ?? "");
  const [searchResults, setSearchResults] = useState<
    Array<MusicBrainzRelease & Partial<WithMedia> & WithArtistCredits>
  >([]);
  const [selectedIndex, setSelectedIndex] = React.useState(-1);

  useEffect(() => {
    // autoFocus property on the input element does not work
    // We need to wait for the modal animated transition to finish
    // and trigger the focus manually.
    setTimeout(() => {
      inputRef?.current?.focus();
    }, 600);
  }, []);

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    if (event.key === "ArrowDown") {
      setSelectedIndex((prevIndex) =>
        prevIndex < searchResults.length - 1 ? prevIndex + 1 : prevIndex
      );
    } else if (event.key === "ArrowUp") {
      setSelectedIndex((prevIndex) =>
        prevIndex > 0 ? prevIndex - 1 : prevIndex
      );
    } else if (event.key === "Enter" && selectedIndex >= 0) {
      onSelectAlbum(searchResults[selectedIndex].id);
      inputRef.current?.blur();
    }
  };

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
          const newReleaseMBID = RELEASE_MBID_REGEXP.exec(
            input
          )?.[2].toLowerCase();
          const newReleaseGroupMBID = RELEASE_GROUP_MBID_REGEXP.exec(
            input
          )?.[2].toLowerCase();
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

  useEffect(() => {
    if (selectedIndex >= 0 && dropdownRef.current) {
      const option = dropdownRef.current.options[selectedIndex];
      option.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  const reset = () => {
    setInputValue("");
    setSearchResults([]);
    onSelectAlbum();
    setSelectedIndex(-1);
  };

  useEffect(() => {
    if (!inputValue) {
      return;
    }
    const isValidUUID =
      RELEASE_MBID_REGEXP.test(inputValue) ||
      RELEASE_GROUP_MBID_REGEXP.test(inputValue);
    if (isValidUUID) {
      throttledHandleValidMBID(inputValue);
    } else {
      throttledSearchRelease(inputValue);
    }
  }, [inputValue, throttledHandleValidMBID, throttledSearchRelease]);

  return (
    <div>
      <div className="input-group album-search">
        <input
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
          ref={inputRef}
          aria-haspopup={Boolean(searchResults?.length)}
          onKeyDown={handleKeyDown}
        />
        <span className="input-group-btn">
          <button className="btn btn-default" type="button" onClick={reset}>
            <FontAwesomeIcon icon={faTimesCircle} />
          </button>
        </span>
        {Boolean(searchResults?.length) && (
          <select
            className="album-search-dropdown"
            onChange={(e) => {
              selectSearchResult(e.currentTarget.value);
              e.target.blur();
            }}
            onKeyDown={handleKeyDown}
            size={Math.min(searchResults.length + 1, 8)}
            tabIndex={-1}
            ref={dropdownRef}
          >
            {searchResults.map((release, index) => {
              return (
                <option
                  key={release.id}
                  value={release.id}
                  style={
                    index === selectedIndex
                      ? { backgroundColor: "#353070", color: "white" }
                      : {}
                  }
                  aria-selected={index === selectedIndex}
                >
                  {release.title}
                  {release.disambiguation && (
                    <small> ({release.disambiguation})</small>
                  )}{" "}
                  -{" "}
                  {release["artist-credit"] &&
                    release["artist-credit"]
                      .map(
                        (artist) =>
                          `${artist.name} ${
                            artist.joinphrase ? artist.joinphrase : ""
                          }`
                      )
                      .join("")}
                  - {release.date && new Date(release.date).getFullYear()}{" "}
                  <small>
                    ({release.media?.map((medium) => medium.format).join(" + ")}
                    )
                  </small>
                </option>
              );
            })}
          </select>
        )}
      </div>
    </div>
  );
}
