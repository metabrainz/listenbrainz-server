import * as React from "react";

type ColorPickerProps = {
  firstColor: string;
  secondColor: string;
  onClick: React.MouseEventHandler;
};

function ColorPicker({ firstColor, secondColor, onClick }: ColorPickerProps) {
  return (
    <button type="button" className="color-picker" onClick={onClick}>
      <div className="color-half" style={{ backgroundColor: firstColor }} />
      <div className="color-half" style={{ backgroundColor: secondColor }} />
    </button>
  );
}

export default ColorPicker;
