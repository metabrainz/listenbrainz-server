import React from "react";
import { ArtistType } from "./artistLookup";
import "./SearchBox.css";
interface SearchItemProps {
    artist: ArtistType;
    key: number;
    onArtistChange: (artist: string) => void;
    onDropdownChange: (openDropdown: boolean) => void;
}

const SearchItem = (props: SearchItemProps) => {
    const handleClick = () => {
        props.onArtistChange(props.artist.id);
        props.onDropdownChange(false);
    };
    return(
        <div 
        className="search-item"
        key={props.key}
        onClick={handleClick}   
        >
            {props.artist.name} - {props.artist.country ?? "Unknown"} 
        </div>
    );
}
export default SearchItem;