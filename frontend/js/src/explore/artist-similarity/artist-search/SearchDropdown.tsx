import React from "react";
import { ArtistType } from "./artistLookup";
import SearchItem from "./SearchItem";

interface SearchDropdownProps {
  searchResults: Array<ArtistType>;
  onArtistChange: (artist: string) => void;
  onDropdownChange: (openDropdown: boolean) => void;
}

function SearchDropdown({
  searchResults,
  onDropdownChange,
  onArtistChange,
}: SearchDropdownProps) {
  return (
    <div className="searchbox-dropdown">
      {searchResults.map((artist) => {
        return (
          <SearchItem
            artist={artist}
            key={artist.id}
            onArtistChange={onArtistChange}
            onDropdownChange={onDropdownChange}
          />
        );
      })}
    </div>
  );
}
export default SearchDropdown;
