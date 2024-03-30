import React, { useMemo, useState } from "react";
import { faSearch, faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import { toast } from "react-toastify";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";

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
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [openDropdown, setOpenDropdown] = useState<boolean>(false);

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
          }
        }
      },
      800,
      { leading: false, trailing: true }
    );
  }, []);

  // Lookup the artist based on the query
  const handleQueryChange = async (query: string) => {
    setSearchQuery(query);
    if (query.length && query.trim().length) {
      setOpenDropdown(true);
    } else {
      setOpenDropdown(false);
    }
    await getArtists(query);
  };

  // Handle button click on an artist in the dropdown list
  const handleButtonClick = (artist: ArtistTypeSearchResult) => {
    onArtistChange(artist.id);
    setOpenDropdown(false);
    setSearchQuery(artist.name);
  };
  const increment = () => {
    onSimilarArtistsLimitChange(currentSimilarArtistsLimit + 1);
  };
  const decrement = () => {
    onSimilarArtistsLimitChange(currentSimilarArtistsLimit - 1);
  };

  return (
    <>
      <div className="input-group track-search">
        <div className="artist-search-input">
          <input
            id="searchbox-artist-name"
            type="text"
            className="form-control"
            name="artist_mbid"
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="Artist name"
            value={searchQuery}
            aria-haspopup={Boolean(searchResults?.length)}
          />
          <button id="searchbox-icon" type="button">
            <FontAwesomeIcon icon={faSearch} color="white" />
          </button>
        </div>
        <div className="track-search-dropdown">
          {openDropdown &&
            searchResults?.map((artist) => {
              return (
                <button
                  type="button"
                  className="search-item"
                  key={artist.id}
                  onClick={() => handleButtonClick(artist)}
                >
                  {`${artist.name} - ${artist.country ?? "Unknown"}`}
                </button>
              );
            })}
        </div>
      </div>
      <div className="graph-size-input">
        <label htmlFor="artist-graph-size-input">Web Size</label>
        <div className="artist-search-input">
          <button id="searchbox-icon" type="button" onClick={decrement}>
            <FontAwesomeIcon icon={faMinus} color="white" />
          </button>
          <input
            id="artist-graph-size-input"
            type="number"
            className="form-control"
            name="graoh_size"
            onChange={(e) =>
              onSimilarArtistsLimitChange(e.target.valueAsNumber)
            }
            placeholder="Graph Size"
            value={currentSimilarArtistsLimit}
          />
          <button id="searchbox-icon" type="button" onClick={increment}>
            <FontAwesomeIcon icon={faPlus} color="white" />
          </button>
        </div>
      </div>
    </>
  );
}
export default SearchBox;
