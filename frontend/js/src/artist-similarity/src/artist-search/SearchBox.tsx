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
    const [similarArtistsLimit, setSimilarArtistsLimit] = React.useState<number>(props.currentsimilarArtistsLimit);
    // Delay before dropdown disappears to make sure user can click on it
    const dropdownDelay = 200;
    const limitInputElemenet = useRef<HTMLInputElement>(null);
    const limit = useRef<number>(props.currentsimilarArtistsLimit);

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
    const handlesimilarArtistsLimitChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
        let limit = event.currentTarget.valueAsNumber;
        props.onSimilarArtistsLimitChange(similarArtistsLimit);
    }
    // Set the artist and similarArtistsLimit based on user input
    /*useEffect(() => {
        props.onSimilarArtistsLimitChange(similarArtistsLimit);
        //props.onArtistChange(artistMbid);
        setSearchQuery("");
    }, [similarArtistsLimit, artistMbid]);*/

    // Hide the dropdown when the user clicks outside of it
    const toggleDropdown = () => setTimeout(() => {
        const dropdown = document.getElementById("search-dropdown");
        dropdown?.style.display === "flex" ? dropdown.style.display = "none" : dropdown!.style.display = "flex";
    }, dropdownDelay);

    const increment = () => {
        setSimilarArtistsLimit(similarArtistsLimit + 1); 
    }
    const decrement = () => {
        //let input = document.getElementById("graph-size-input-number") as HTMLInputElement;
        //input.stepDown();
        // Dispatch change event to trigger onChange, so the custom buttons also trigger the event
        //input.dispatchEvent(new Event('change', { bubbles: true }));
        //limit.current = limit.current - 1;
        //setSimilarArtistsLimit(limit.current);
        setSimilarArtistsLimit(similarArtistsLimit + 1);
        //props.onSimilarArtistsLimitChange(input.valueAsNumber);
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
            value={similarArtistsLimit}
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
