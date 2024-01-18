import * as React from "react";
import GalleryTile from "./GalleryTile";
import { TemplateOption, TemplateNameEnum } from "../ArtCreator";

type GalleryProps = {
  currentStyle: TemplateOption;
  options: TemplateOption[];
  onStyleSelect: (styleName: TemplateNameEnum) => void;
};

function Gallery(props: GalleryProps) {
  const { currentStyle, options, onStyleSelect } = props;
  return (
    <div className="stats-art-gallery">
      {options.map((opt) => (
        <GalleryTile
          key={opt.name}
          templateOption={opt}
          onStyleSelect={onStyleSelect}
          isSelected={currentStyle.name === opt.name}
        />
      ))}
    </div>
  );
}

export default Gallery;
