import * as React from "react";
import {
  useBrainzPlayerDispatch,
  useBrainzPlayerContext,
} from "./BrainzPlayerContext";

const STORAGE_KEY = "brainzplayer-volume";

function VolumeControlButton() {
  const dispatch = useBrainzPlayerDispatch();
  const { isActivated } = useBrainzPlayerContext();
  const [volume, setVolume] = React.useState(() => {
    const savedVolume = localStorage.getItem(STORAGE_KEY);
    return savedVolume !== null ? Number(savedVolume) : 100;
  });

  React.useEffect(() => {
    if (isActivated) {
      dispatch({ type: "VOLUME_CHANGE", data: volume });
    }
  }, [isActivated, volume, dispatch]);

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = Number(e.target.value);
    setVolume(newVolume);
    localStorage.setItem(STORAGE_KEY, newVolume.toString());
  };
  return (
    <input
      onChange={handleVolumeChange}
      className="volume-input"
      type="range"
      value={volume}
      max="100"
      min="0"
      step="5"
    />
  );
}

export default VolumeControlButton;
