import React from "react";
import { ArtistType } from "./SearchBox";
import SearchItem from "./SearchItem";

interface SearchDropdownProps {
    searchResults: Array<ArtistType>;
    onArtistChange: (artist: ArtistType) => void;
}

const SearchDropdown = (props: SearchDropdownProps) => {
    return(
        <div id="search-dropdown"
        onClick={(e) => {e.currentTarget.style.display === "flex" ? e.currentTarget.style.display = "none" : e.currentTarget.style.display = "flex";}}
        style={
            {
                display: "none",
                position: "absolute",
                flexDirection: "column",
                backgroundColor: "white",
                maxHeight: "25vh",
                overflow: "scroll",
                width: "inherit",
            }
        }>
            {props.searchResults.map((artist, index) => {
                return(
                    <SearchItem artist={artist} key={index} onArtistChange={props.onArtistChange}/>
                );
            }
            )}
        </div>
    );
}
export default SearchDropdown;
