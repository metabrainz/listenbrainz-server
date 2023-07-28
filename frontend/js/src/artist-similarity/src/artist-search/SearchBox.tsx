import React, { useEffect, useMemo, useRef, useState } from "react";
import SearchDropdown from "./SearchDropdown";
import artistLookup from "./artistLookup";
import { ArtistType } from "./artistLookup";
import { faMagnifyingGlass, faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import "./SearchBox.css";
interface SearchBoxProps {
    currentsimilarArtistsLimit: number;
    onSimilarArtistsLimitChange: (similarArtistsLimit: number) => void;
    onArtistChange: (artist_mbid: string) => void;
}

const SearchBox = (props: SearchBoxProps) => {
    // State to store the search results (list of artists)
    const [searchResults, setSearchResults] = React.useState<Array<ArtistType>>([]);
    const [searchQuery, setSearchQuery] = React.useState<string>("");
    // State to toggle the dropdown menu for search
    const [openDropdown, setOpenDropdown] = useState(false);

    // Lookup the artist based on the query
    const getArtists = async (): Promise<void> => {
        if(searchQuery.length && searchQuery.trim() !== ""){
            const results = await artistLookup(searchQuery);
            setSearchResults(results ?? []);
            // Open the dropdown if any results exist
            if(searchResults.length) {
                setOpenDropdown(true);
            }
        }
        else{
            setSearchResults([]);
        }
    }
    // Lookup the artist based on the query
    useEffect(() => {
        getArtists();
    }, [searchQuery]);
    
    const increment = () => {
        props.onSimilarArtistsLimitChange(props.currentsimilarArtistsLimit + 1);
    }
    const decrement = () => {
        props.onSimilarArtistsLimitChange(props.currentsimilarArtistsLimit - 1);
    }
    return (
        <form
        className="search-box"
        autoComplete="off"
        >
            <div
            className="artist-input"
            >
                <div
                className="artist-input-box"
                >
                    <input 
                    id="artist-input-name" 
                    type="search"
                    name="artist_mbid" 
                    placeholder="Artist name" 
                    onChange={e => setSearchQuery(e.target.value)}
                    value={searchQuery}
                />
                    <button 
                    id="artist-input-icon"
                    type="button"
                    >
                        <FontAwesomeIcon 
                        icon={faMagnifyingGlass} 
                        color="white"
                        />   
                    </button>
                </div>
                {openDropdown && (
                    <SearchDropdown 
                    searchResults={searchResults} 
                    onArtistChange={props.onArtistChange}
                    onDropdownChange={setOpenDropdown} 
                    id={"search-dropdown"}
                    />)
                }
            </div>
            <div
            className="graph-size-input"
            >
            <label 
            id="graph-size-input-label"
            >
                Web size:
            </label>
            <button
            id="graph-size-input-minus"
            type="button"
            onClick={decrement}
            >
                <FontAwesomeIcon 
                icon={faMinus} 
                color="white"
                />
            </button>
            <input 
            id="graph-size-input-number" 
            type="number" 
            name="similarArtistsLimit" 
            placeholder="Graph size"   
            onChange={e => props.onSimilarArtistsLimitChange(e.target.valueAsNumber)} 
            value={props.currentsimilarArtistsLimit}
            required
            />
            <span 
            id="graph-size-input-warning" 
            className="validity"
            >
            </span>
            <button
            id="graph-size-input-plus"
            type="button"
            onClick={increment}
            >
                <FontAwesomeIcon 
                icon={faPlus} 
                color="white"
                />
            </button>
            </div>
        </form>
    );
}
export default SearchBox;
