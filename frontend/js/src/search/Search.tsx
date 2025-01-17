import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { faMagnifyingGlass, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Helmet } from "react-helmet";
import _ from "lodash";
import Pill from "../components/Pill";
import ArtistSearch from "./ArtistSearch";
import TrackSearch from "./TrackSearch";
import UserSearch from "./UserSearch";
import AlbumSearch from "./AlbumSearch";
import PlaylistSearch from "./PlaylistSearch";

const invalidSearchTypes = (searchType?: string) => {
  if (!searchType) {
    return true;
  }
  return !["artist", "album", "track", "playlist", "user"].includes(searchType);
};

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get("search_term") || "";
  const searchType = searchParams.get("search_type") || "";

  React.useEffect(() => {
    if (invalidSearchTypes(searchType)) {
      setSearchParams(
        { search_term: searchTerm, search_type: "artist" },
        { replace: true }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchType]);

  const setSearchType = (newSearchType: string) => {
    setSearchParams({ search_term: searchTerm, search_type: newSearchType });
  };

  const [searchTermInput, setSearchTermInput] = React.useState(searchTerm);

  const search = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchTermInput) {
      return;
    }
    setSearchParams({ search_term: searchTermInput, search_type: searchType });
  };

  const searchTermValid = searchTerm.trim();

  React.useEffect(() => {
    setSearchTermInput(searchTerm);
  }, [searchTerm]);

  const activeLabel = _.capitalize(searchType);

  return (
    <>
      <Helmet>
        <title>Search Results - {searchTerm}</title>
      </Helmet>
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/search/">Search</Link>
          </li>
          {activeLabel && <li className="active">{activeLabel}</li>}
        </ol>
      </div>
      <div role="main">
        <form className="form-group" onSubmit={search}>
          <h2
            className="header-with-line"
            style={{ alignItems: "center", flexWrap: "wrap" }}
          >
            <div className="search-result-header">
              Search results for
              <strong style={{ marginLeft: "5px" }}>{searchTerm}</strong>
            </div>
            <div
              className="search-bar"
              style={{
                order: 3,
                marginTop: 0,
                marginRight: "2em",
              }}
            >
              <input
                type="text"
                className="form-control input-lg"
                name="search_term"
                placeholder="Search"
                value={searchTermInput}
                onChange={(e) => setSearchTermInput(e.target.value)}
                required
              />
              <button type="submit">
                <FontAwesomeIcon icon={faMagnifyingGlass} size="sm" />
              </button>
            </div>
          </h2>
        </form>
        <div style={{ marginBottom: "20px" }}>
          <Pill
            id="search-type-artist"
            onClick={() => {
              setSearchType("artist");
            }}
            active={searchType === "artist"}
            type="secondary"
          >
            Artists
          </Pill>
          <Pill
            id="search-type-album"
            onClick={() => {
              setSearchType("album");
            }}
            active={searchType === "album"}
            type="secondary"
          >
            Albums
          </Pill>
          <Pill
            id="search-type-track"
            onClick={() => {
              setSearchType("track");
            }}
            active={searchType === "track"}
            type="secondary"
          >
            Tracks
          </Pill>
          <Pill
            id="search-type-playlist"
            onClick={() => {
              setSearchType("playlist");
            }}
            active={searchType === "playlist"}
            type="secondary"
          >
            Playlists
          </Pill>
          <Pill
            id="search-type-user"
            onClick={() => {
              setSearchType("user");
            }}
            active={searchType === "user"}
            type="secondary"
          >
            Users
          </Pill>
        </div>

        {!searchTermValid && (
          <div className="alert alert-info">
            <strong>Search for something!</strong> Enter a search term in the
            search bar above to get started.
          </div>
        )}
        {searchType === "artist" && searchTermValid && (
          <ArtistSearch searchQuery={searchTerm} />
        )}
        {searchType === "track" && searchTermValid && (
          <TrackSearch searchQuery={searchTerm} />
        )}
        {searchType === "user" && searchTermValid && (
          <UserSearch searchQuery={searchTerm} />
        )}
        {searchType === "album" && searchTermValid && (
          <AlbumSearch searchQuery={searchTerm} />
        )}
        {searchType === "playlist" && searchTermValid && (
          <PlaylistSearch searchQuery={searchTerm} />
        )}
      </div>
    </>
  );
}
