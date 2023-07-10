import * as React from "react";
import { useCallback } from "react";

enum StyleEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
}
type GalleryTileProps = {
  name: StyleEnum;
  url: string;
  isSelected: Boolean;
  onStyleSelect: (styleName: string) => void;
};

function GalleryTile(props: GalleryTileProps) {
  const { name, url, onStyleSelect, isSelected } = props;
  const updateStyleCallback = useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      onStyleSelect(name);
    },
    [name, onStyleSelect]
  );

  return (
    <div
      role="presentation"
      onClick={updateStyleCallback}
      className="galleryItem"
    >
      <object
        title="galleryTile"
        className={isSelected ? "selected-gallery-tile" : "gallery-tile"}
        data={url}
      />
    </div>
  );
}
export default GalleryTile;
