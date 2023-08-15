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
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events,jsx-a11y/no-static-element-interactions
    <div className="search-item" key={key} onClick={handleClick}>
      {artist.name} - {artist.country ?? "Unknown"}
    </div>
  );
}
export default SearchItem;
