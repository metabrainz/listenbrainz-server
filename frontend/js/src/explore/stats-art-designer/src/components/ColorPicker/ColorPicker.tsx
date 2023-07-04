import "./ColorPicker.css";

type ColorPickerProps = {
    firstColor: string;
    secondColor: string;
}

const ColorPicker = ({ firstColor, secondColor }: ColorPickerProps) => {
  return (
    <div className="color-picker">
      <div 
        className="color-half" 
        style={{ backgroundColor: firstColor }}>    
    </div>
      <div
        className="color-half"
        style={{ backgroundColor: secondColor }}
      ></div>
    </div>
  );
};

export default ColorPicker;
