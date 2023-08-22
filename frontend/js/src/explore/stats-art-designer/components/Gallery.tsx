import * as React from "react";
import GalleryTile from "./GalleryTile";

enum StyleEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
}

type GalleryOption = {
  name: StyleEnum;
  url: string;
};

type GalleryProps = {
  currentStyle: StyleEnum;
  galleryOpts: GalleryOption[];
  onStyleSelect: (styleName: string) => void;
};

function Gallery(props: GalleryProps) {
  const { currentStyle, galleryOpts, onStyleSelect } = props;
  return (
    <div className="stats-art-gallery">
      {galleryOpts.map((opt) => (
        <GalleryTile
          key={opt.name}
          name={opt.name}
          onStyleSelect={onStyleSelect}
          isSelected={currentStyle === opt.name}
          url={opt.url}
        />
      ))}
    </div>
  );
}

export default Gallery;
