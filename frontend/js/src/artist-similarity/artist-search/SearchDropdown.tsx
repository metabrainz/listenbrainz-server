import React from "react";
import { ArtistType } from "./artistLookup";
import SearchItem from "./SearchItem";

interface SearchDropdownProps {
  searchResults: Array<ArtistType>;
  onArtistChange: (artist: string) => void;
  id: string;
  onDropdownChange: (openDropdown: boolean) => void;
}

function SearchDropdown({
  searchResults,
  onDropdownChange,
  onArtistChange,
  id,
}: SearchDropdownProps) {
  return (
    <div id={id}>
      {searchResults.map((artist, index) => {
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
