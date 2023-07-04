import * as React from "react";
import "./ToggleOption.css";

type ToggleOptionProps = {
  buttonName: string;
  onClick: () => void;
}

const ToggleOption = ({buttonName, onClick}: ToggleOptionProps) => {
  return (
    <div className="cl-toggle-switch" onClick={onClick}>
        <label className="cl-switch">
            <input type="checkbox"/>
            <span></span>
        </label>
        {buttonName}
    </div> 
  )
}

export default ToggleOption;
