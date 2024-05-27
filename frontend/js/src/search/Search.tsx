import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { faMagnifyingGlass, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Pill from "../components/Pill";
import ArtistSearch from "./ArtistSearch";
import SongSearch from "./SongSearch";

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get("search_term") || "";

  const [searchTermInput, setSearchTermInput] = React.useState(searchTerm);
  const [searchType, setSearchType] = React.useState<
    "artist" | "album" | "song" | "playlist" | "user"
  >("artist");

  const search = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchTermInput) {
      return;
    }
    setSearchParams({ search_term: searchTermInput });
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
          <h2 className="header-with-line">
            Search Results for
            <strong style={{ marginLeft: "5px" }}>{searchTerm}</strong>
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
                placeholder="Not found yet?"
                value={searchTermInput}
                onChange={(e) => setSearchTermInput(e.target.value)}
                required
              />
              <button type="submit">
                <FontAwesomeIcon icon={faMagnifyingGlass} />
              </button>
            </div>
          </h2>
        </form>
        <div className="row">
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
      </div>
    </>
  );
}
