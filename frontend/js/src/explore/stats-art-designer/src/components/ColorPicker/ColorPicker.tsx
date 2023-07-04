import * as React from "react";
import "./ColorPicker.css";

type ColorPickerProps = {
  firstColor: string;
  secondColor: string;
};

function ColorPicker({ firstColor, secondColor }: ColorPickerProps) {
  return (
    <div className="color-picker">
      <div className="color-half" style={{ backgroundColor: firstColor }} />
      <div className="color-half" style={{ backgroundColor: secondColor }} />
    </div>
  );
}

export default ColorPicker;
