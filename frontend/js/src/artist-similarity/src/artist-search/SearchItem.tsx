import React from "react";
import { ArtistType } from "./SearchBox";
import { doc } from "prettier";

interface SearchItemProps {
    artist: ArtistType;
    key: number;
    onArtistChange: (artist: ArtistType) => void;
}

const SearchItem = (props: SearchItemProps) => {
    return(
        <div 
        className="search-item"
        onClick={() => 
            {
                props.onArtistChange(props.artist);
                document.getElementById("search-dropdown")!.style.display = "none";
                (document.getElementById("artist-input") as HTMLInputElement)!.value = props.artist.name + " - " + props.artist.country;
            }}
        style={
            {
                position: "relative",
                padding: "0.5vh",
                cursor: "pointer",
                backgroundColor: "white",
                zIndex: 1,
            }
        }
        onMouseEnter={(e) => {e.currentTarget.style.backgroundColor = "lightgrey";}}
        onMouseLeave={(e) => {e.currentTarget.style.backgroundColor = "white";}}    
        >
        {props.artist.name} - {props.artist.country} 
        </div>
    );
}
export default SearchItem;