import React from "react";
import { ArtistType } from "./ArtistLookup";
import "./SearchBox.css";
interface SearchItemProps {
    artist: ArtistType;
    key: number;
    onArtistChange: (artist: string) => void;
}

const SearchItem = (props: SearchItemProps) => {
    return(
        <div 
        className="search-item"
        onClick={() => props.onArtistChange(props.artist.id)}   
        >
            {props.artist.name} - {props.artist.country ?? "Unknown"} 
        </div>
    );
}
export default SearchItem;