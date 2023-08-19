import React, { useCallback, useMemo, useState } from "react";
import { faSearch, faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import { toast } from "react-toastify";
import artistLookup, { ArtistType } from "./artistLookup";
import { ToastMsg } from "../../../notifications/Notifications";

interface SearchBoxProps {
  currentsimilarArtistsLimit: number;
  onSimilarArtistsLimitChange: (similarArtistsLimit: number) => void;
  onArtistChange: (artist_mbid: string) => void;
}

function SearchBox({
  currentsimilarArtistsLimit,
  onSimilarArtistsLimitChange,
  onArtistChange,
}: SearchBoxProps) {
  // State to store the search results (list of artists)
  const [searchResults, setSearchResults] = useState<Array<ArtistType>>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  // State to toggle the dropdown menu for search
  const [openDropdown, setOpenDropdown] = useState<boolean>(false);

  const getArtists = useCallback(async (query: string) => {
    if (query.length && query.trim().length) {
      try {
        const results = await artistLookup(query);
        setSearchResults(results);
        setOpenDropdown(true);
      } catch (error) {
        setSearchResults([]);
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    }
  }, []);

  const throttledGetArtists = useMemo(() => {
    return throttle(getArtists, 800, { leading: false, trailing: true });
  }, [getArtists]);

  // Lookup the artist based on the query
  const handleQueryChange = async (query: string) => {
    setSearchQuery(query);
    await throttledGetArtists(query);
  };

  // Handle button click on an artist in the dropdown list
  const handleButtonClick = (artist: ArtistType) => {
    onArtistChange(artist.id);
    setOpenDropdown(false);
  };
  const increment = () => {
    onSimilarArtistsLimitChange(currentsimilarArtistsLimit + 1);
  };
  const decrement = () => {
    onSimilarArtistsLimitChange(currentsimilarArtistsLimit - 1);
  };
  return (
    <form className="user-inputs-container" autoComplete="off">
      <div
        className="artist-input-container"
        onFocus={() => searchResults.length && setOpenDropdown(true)}
        onBlur={() => setTimeout(() => setOpenDropdown(false), 100)}
      >
        <div className="searchbox-container">
          <input
            id="searchbox-artist-name"
            type="search"
            name="artist_mbid"
            placeholder="Artist name"
            onChange={(e) => handleQueryChange(e.target.value)}
            value={searchQuery}
          />
          <button id="searchbox-icon" type="button">
            <FontAwesomeIcon icon={faSearch} color="white" />
          </button>
        </div>
        <div className="searchbox-dropdown-container">
          {openDropdown && Boolean(searchResults?.length) && (
            <div className="searchbox-dropdown">
              {searchResults.map((artist) => {
                return (
                  <button
                    type="button"
                    className="search-item"
                    key={artist.id}
                    onClick={() => handleButtonClick(artist)}
                  >
                    {artist.name} - {artist.country ?? "Unknown"}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
      <div className="graph-size-input-container">
        <label htmlFor="graph-size-input-number" id="graph-size-input-label">
          Web size:
        </label>
        <button
          id="graph-size-input-icon-minus"
          type="button"
          onClick={decrement}
        >
          <FontAwesomeIcon icon={faMinus} color="white" />
        </button>
        <input
          id="graph-size-input-number"
          type="number"
          name="similarArtistsLimit"
          placeholder="Graph size"
          size={2}
          onChange={(e) => onSimilarArtistsLimitChange(e.target.valueAsNumber)}
          value={currentsimilarArtistsLimit}
          required
        />
        <span id="graph-size-input-warning" className="validity" />
        <button
          id="graph-size-input-icon-plus"
          type="button"
          onClick={increment}
        >
          <FontAwesomeIcon icon={faPlus} color="white" />
        </button>
      </div>
    </form>
  );
}
export default SearchBox;
