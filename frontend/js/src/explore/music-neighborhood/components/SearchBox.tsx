import React, { useMemo, useState } from "react";
import {
  faSearch,
  faMinus,
  faPlus,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import { toast } from "react-toastify";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import DropdownRef from "../../../utils/Dropdown";

interface SearchBoxProps {
  currentSimilarArtistsLimit: number;
  onSimilarArtistsLimitChange: (similarArtistsLimit: number) => void;
  onArtistChange: (artist_mbid: string) => void;
}

type ArtistTypeSearchResult = {
  name: string;
  id: string;
  type?: string;
  country?: string;
};

function SearchBox({
  currentSimilarArtistsLimit,
  onSimilarArtistsLimitChange,
  onArtistChange,
}: SearchBoxProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  // State to store the search results (list of artists)
  const [searchResults, setSearchResults] = useState<
    Array<ArtistTypeSearchResult>
  >([]);
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  const dropdownRef = DropdownRef();
  const searchInputRef = React.useRef<HTMLInputElement>(null);
  const [loading, setLoading] = React.useState(false);

  const getArtists = useMemo(() => {
    return throttle(
      async (query: string) => {
        if (query.length && query.trim().length) {
          try {
            const results = await APIService.artistLookup(query);
            const { artists } = results;
            setSearchResults(artists);
          } catch (error) {
            setSearchResults([]);
            toast.error(
              <ToastMsg
                title="Search Error"
                message={typeof error === "object" ? error.message : error}
              />,
              { toastId: "error" }
            );
          } finally {
            setLoading(false);
          }
        }
      },
      800,
      { leading: false, trailing: true }
    );
  }, []);

  // Handle button click on an artist in the dropdown list
  const handleButtonClick = (artistId: string) => {
    onArtistChange(artistId);
  };
  const increment = () => {
    onSimilarArtistsLimitChange(currentSimilarArtistsLimit + 1);
  };
  const decrement = () => {
    onSimilarArtistsLimitChange(currentSimilarArtistsLimit - 1);
  };

  const reset = () => {
    setSearchQuery("");
    setSearchResults([]);
    setLoading(false);
    searchInputRef?.current?.focus();
  };

  React.useEffect(() => {
    if (!searchQuery) {
      return;
    }
    setLoading(true);
    getArtists(searchQuery);
  }, [searchQuery, getArtists]);

  return (
    <>
      <div>
        <label htmlFor="searchbox-artist-name">Artist name</label>
        <div
          className="input-group dropdown-search"
          ref={dropdownRef}
          id="artist-search-box"
        >
          <input
            ref={searchInputRef}
            id="searchbox-artist-name"
            type="search"
            className="form-control"
            name="artist_mbid"
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Artist name"
            value={searchQuery}
            aria-haspopup={Boolean(searchResults?.length)}
            required
          />
          <button
            className="btn btn-info"
            type="button"
            onClick={reset}
            id="artist-search-button"
          >
            {loading ? (
              <FontAwesomeIcon icon={faSpinner} spin />
            ) : (
              <FontAwesomeIcon icon={faSearch} />
            )}
          </button>
          {Boolean(searchResults?.length) && (
            <select
              className="dropdown-search-suggestions"
              onChange={(e) => {
                if (!e.currentTarget.value) {
                  // clicked on "no more options"
                  return;
                }
                setSearchQuery(e.currentTarget.selectedOptions[0].text);
                handleButtonClick(e.currentTarget.value);
                e.target.blur();
              }}
              size={Math.min(searchResults.length + 1, 8)}
              tabIndex={-1}
            >
              {searchResults.map((artist, index) => {
                const artistInfoString = `${artist.name} - ${
                  artist.country ?? "Unknown"
                }`;
                return (
                  <option
                    key={artist.id}
                    value={artist.id}
                    data-release-info={artistInfoString}
                    title={artistInfoString}
                  >
                    {artistInfoString}
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
      <div>
        <label htmlFor="artist-graph-size-input">Web size</label>
        <div className="input-group artist-search-input">
          <button
            className="btn btn-info btn-sm"
            type="button"
            onClick={decrement}
          >
            <FontAwesomeIcon icon={faMinus} color="white" />
          </button>
          <input
            id="artist-graph-size-input"
            type="number"
            className="form-control text-center"
            name="graph_size"
            onChange={(e) =>
              onSimilarArtistsLimitChange(e.target.valueAsNumber)
            }
            placeholder="Graph Size"
            value={currentSimilarArtistsLimit}
          />
          <button
            className="btn btn-info btn-sm"
            type="button"
            onClick={increment}
          >
            <FontAwesomeIcon icon={faPlus} color="white" />
          </button>
        </div>
      </div>
    </>
  );
}
export default SearchBox;
