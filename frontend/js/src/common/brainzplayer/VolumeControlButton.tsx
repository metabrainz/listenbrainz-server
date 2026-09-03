import * as React from "react";
import { useAtom } from "jotai";

import { volumeAtom } from "./BrainzPlayerAtoms";

function VolumeControlButton() {
  const [volume, setVolume] = useAtom(volumeAtom);

  return (
    <input
      onChange={(e) => setVolume(Number(e.target.value))}
      className="volume-input"
      type="range"
      value={volume}
      max="100"
      min="0"
      step="5"
    />
  );
}

export default React.memo(VolumeControlButton);
