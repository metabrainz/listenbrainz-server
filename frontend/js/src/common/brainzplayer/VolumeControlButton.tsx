import * as React from "react";
import { useBrainzPlayerDispatch } from "./BrainzPlayerContext";

function VolumeControlButton() {
  const dispatch = useBrainzPlayerDispatch();
  const handleVolumeChange = (e: React.MouseEvent<HTMLInputElement>) => {
    dispatch({
      type: "VOLUME_CHANGE",
      data: e.currentTarget?.value ?? 100,
    });
  };
  return (
    <input
      onMouseUp={handleVolumeChange}
      className="volume-input"
      type="range"
      defaultValue="100"
      max="100"
      min="0"
      step="5"
    />
  );
}

export default VolumeControlButton;
