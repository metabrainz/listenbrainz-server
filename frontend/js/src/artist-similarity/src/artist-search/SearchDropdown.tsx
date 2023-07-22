import React from "react";
import { ArtistType } from "./ArtistLookup";
import SearchItem from "./SearchItem";
import "./SearchBox.css";
interface SearchDropdownProps {
    searchResults: Array<ArtistType>;
    onArtistChange: (artist: string) => void;
    id: string;
}

const SearchDropdown = (props: SearchDropdownProps) => {
    return(
        <div 
        id={props.id}
        >
            {props.searchResults.map((artist, index) => {
                return(
                    <SearchItem 
                    artist={artist} 
                    key={index} 
                    onArtistChange={props.onArtistChange}
                    />
                );
            }
            )}
        </div>
    );
}
export default SearchDropdown;
