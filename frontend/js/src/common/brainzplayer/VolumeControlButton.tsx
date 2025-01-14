import * as React from "react";
import { useBrainzPlayerDispatch } from "./BrainzPlayerContext";

type VolumeControlButtonProps = {
  volume: number;
};

function VolumeControlButton(props: VolumeControlButtonProps) {
  const dispatch = useBrainzPlayerDispatch();
  const volumeRef = React.useRef<HTMLInputElement>(null);
  const handleVolumeChange = () => {
    dispatch({
      type: "VOLUME_CHANGE",
      data: volumeRef?.current?.value ?? 100,
    });
  };
  return (
    <input
      ref={volumeRef}
      onMouseUp={handleVolumeChange}
      className="volume"
      type="range"
      defaultValue="100"
      max="100"
      min="0"
      step="5"
    />
  );
}

export default VolumeControlButton;
