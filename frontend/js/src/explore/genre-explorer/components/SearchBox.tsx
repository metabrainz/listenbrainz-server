import * as React from "react";
import { useState, useMemo } from "react";
import { faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Fuse from "fuse.js";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import DropdownRef from "../../../utils/Dropdown";

interface SearchBoxProps {
  onGenreSelect: (genre: string) => void;
}

export default function SearchBox({ onGenreSelect }: SearchBoxProps) {
  const { musicbrainzGenres } = React.useContext(GlobalAppContext);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Array<string>>([]);
  const dropdownRef = DropdownRef();
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // Initialize Fuse for fuzzy search
  const fuse = useMemo(() => {
    const fuseOptions = {
      threshold: 0.3,
      minMatchCharLength: 2,
    };
    return new Fuse(musicbrainzGenres || [], fuseOptions);
  }, [musicbrainzGenres]);

  // Handle search input changes
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);

    if (query.trim()) {
      const results = fuse.search(query);
      setSearchResults(results.map((result) => result.item).slice(0, 25));
    } else {
      setSearchResults([]);
    }
  };

  const reset = () => {
    setSearchQuery("");
    setSearchResults([]);
    searchInputRef?.current?.focus();
  };

  return (
    <div className="genre-search-box">
      <label htmlFor="searchbox-genre-name">Genre name</label>
      <div
        className="input-group dropdown-search"
        ref={dropdownRef}
        id="genre-search-box"
      >
        <input
          ref={searchInputRef}
          id="searchbox-genre-name"
          type="search"
          className="form-control"
          name="genre_name"
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search genres..."
          value={searchQuery}
          aria-haspopup={Boolean(searchResults?.length)}
          required
        />
        <button
          className="btn btn-info"
          type="button"
          onClick={reset}
          id="genre-search-button"
        >
          <FontAwesomeIcon icon={faSearch} />
        </button>
        {Boolean(searchResults?.length) && (
          <select
            className="dropdown-search-suggestions"
            onChange={(e) => {
              if (!e.currentTarget.value) {
                return;
              }
              setSearchQuery(e.currentTarget.value);
              onGenreSelect(e.currentTarget.value);
              e.target.blur();
            }}
            size={Math.min(searchResults.length + 1, 8)}
            tabIndex={-1}
          >
            {searchResults.map((genre) => (
              <option key={genre} value={genre} title={genre}>
                {genre}
              </option>
            ))}
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
}
