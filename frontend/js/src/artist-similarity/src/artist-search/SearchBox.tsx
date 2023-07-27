import React, { useEffect, useMemo, useRef } from "react";
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
    // Delay before dropdown disappears to make sure user can click on it
    const dropdownDelay = 200;
    const limitInputElemenet = useRef<HTMLInputElement>(null);
    
    // Lookup the artist based on the query
    const getArtists = async (): Promise<void> => {
        if(searchQuery.length && searchQuery.trim() !== ""){
            const results = await artistLookup(searchQuery);
            setSearchResults(results ?? []);
        }
        else{
            setSearchResults([]);
        }
    }
    // Lookup the artist based on the query
    useEffect(() => {
        getArtists();
    }, [searchQuery]);
    
    // Set similarArtistsLimit based on user input
    const handlesimilarArtistsLimitChange = (): void => {
        let limit = limitInputElemenet.current?.valueAsNumber;
        if(limit)
            props.onSimilarArtistsLimitChange(limit);
    }

    // Hide the dropdown when the user clicks outside of it
    const toggleDropdown = () => setTimeout(() => {
        const dropdown = document.getElementById("search-dropdown");
        dropdown?.style.display === "flex" ? dropdown.style.display = "none" : dropdown!.style.display = "flex";
    }, dropdownDelay);

    const increment = () => {
        limitInputElemenet.current?.stepUp();
        // Trigger the onChange Event for the input number manually
        limitInputElemenet.current?.dispatchEvent(new Event('change', {bubbles: true}));
    }
    const decrement = () => {
        limitInputElemenet.current?.stepDown();
        limitInputElemenet.current?.dispatchEvent(new Event('change', {bubbles: true}));
    }
    return (
        <form
        className="search-box"
        autoComplete="off"
        >
            <div
            className="artist-input"
            onFocus={toggleDropdown}
            onBlur={toggleDropdown}
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
                <SearchDropdown 
                searchResults={searchResults} 
                onArtistChange={props.onArtistChange} 
                id={"search-dropdown"}
                />
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
            min="1" max="25"  
            onChange={handlesimilarArtistsLimitChange} 
            defaultValue={props.currentsimilarArtistsLimit}
            ref={limitInputElemenet}
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
