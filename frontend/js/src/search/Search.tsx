import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { faMagnifyingGlass, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Pill from "../components/Pill";
import ArtistSearch from "./ArtistSearch";
import SongSearch from "./SongSearch";
import UserSearch from "./UserSearch";
import AlbumSearch from "./AlbumSearch";

const invalidSearchTypes = (searchType?: string) => {
  if (!searchType) {
    return true;
  }
  return !["artist", "album", "song", "playlist", "user"].includes(searchType);
};

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get("search_term") || "";
  const searchType = searchParams.get("search_type");

  if (invalidSearchTypes(searchType!)) {
    setSearchParams({ search_term: searchTerm, search_type: "artist" });
  }

  const setSearchType = (newSearchType: string) => {
    setSearchParams({ search_term: searchTerm, search_type: newSearchType });
  };

  const [searchTermInput, setSearchTermInput] = React.useState(searchTerm);

  const search = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchTermInput) {
      return;
    }
    setSearchParams({ search_term: searchTermInput, search_type: searchType! });
  };

  return (
    <>
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <Link to="/search/">Search Results</Link>
          </li>
        </ol>
      </div>
      <div role="main">
        <form className="form-group row" onSubmit={search}>
          <h2 className="header-with-line" style={{ alignItems: "center" }}>
            <div>
              Search Results for
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
        <div className="row" style={{ marginBottom: "20px" }}>
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
            id="search-type-song"
            onClick={() => {
              setSearchType("song");
            }}
            active={searchType === "song"}
            type="secondary"
          >
            Songs
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

        {searchType === "artist" && <ArtistSearch searchQuery={searchTerm} />}
        {searchType === "song" && <SongSearch searchQuery={searchTerm} />}
        {searchType === "user" && <UserSearch searchQuery={searchTerm} />}
        {searchType === "album" && <AlbumSearch searchQuery={searchTerm} />}
      </div>
    </>
  );
}
