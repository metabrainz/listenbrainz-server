import * as React from "react";
import { useCallback } from "react";
import { TemplateNameEnum, TemplateOption } from "../ArtCreator";

type GalleryTileProps = {
  templateOption: TemplateOption;
  isSelected: Boolean;
  onStyleSelect: (styleName: TemplateNameEnum) => void;
};

function GalleryTile(props: GalleryTileProps) {
  const { templateOption, onStyleSelect, isSelected } = props;
  const updateStyleCallback = useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      onStyleSelect(templateOption.name);
    },
    [templateOption.name, onStyleSelect]
  );
  let tileCSSClasses = "gallery-tile";
  if (isSelected) {
    tileCSSClasses += " selected";
  }
  return (
    <div
      role="presentation"
      onClick={updateStyleCallback}
      className="gallery-item"
    >
      <img
        title={templateOption.name}
        aria-label={templateOption.name}
        className={tileCSSClasses}
        src={templateOption.image}
      />
    </div>
  );
}
export default GalleryTile;
