import React from "react";
import { ArtistType } from "./artistLookup";

interface SearchItemProps {
  artist: ArtistType;
  key: string;
  onArtistChange: (artist: string) => void;
  onDropdownChange: (openDropdown: boolean) => void;
}

function SearchItem({
  artist,
  key,
  onArtistChange,
  onDropdownChange,
}: SearchItemProps) {
  const handleClick = () => {
    onArtistChange(artist.id);
    onDropdownChange(false);
  };
  return (
    <button
      type="button"
      className="search-item"
      key={key}
      onClick={handleClick}
    >
      {artist.name} - {artist.country ?? "Unknown"}
    </button>
  );
}
export default SearchItem;
