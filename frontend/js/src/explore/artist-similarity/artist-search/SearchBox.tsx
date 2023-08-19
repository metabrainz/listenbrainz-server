import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { faSearch, faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import { ToastContainer, toast } from "react-toastify";
import SearchDropdown from "./SearchDropdown";
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

  /**
   * Solution:
   *  I was able to look up an article for the problem, https://www.developerway.com/posts/debouncing-in-react
   *  The solution works as expected but I feel like it might be a bit hard to understand what's going on.
   */

  /*
  const getArtists = useCallback(async () => {
    if (searchQuery.length && searchQuery.trim().length) {
      try {
        const results = await artistLookup(searchQuery);
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
  }, [searchQuery]);
 
  const getArtistsRef = useRef(getArtists);

  useEffect(() => {
    // Update the getArtists reference when searchQuery gets updated.
    getArtistsRef.current = getArtists;
  }, [getArtists, searchQuery]);

  // Create a throttled function using the current reference of getArtists
  const throttledGetArtists = useMemo(() => {
    return throttle(
      () => {
        getArtistsRef.current?.();
      },
      800,
      { leading: false, trailing: true }
    );
  }, []);
  */
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
  const handleQueryChange = (query: string) => {
    setSearchQuery(query);
    throttledGetArtists(query);
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
            <SearchDropdown
              searchResults={searchResults}
              onArtistChange={onArtistChange}
              onDropdownChange={setOpenDropdown}
            />
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
