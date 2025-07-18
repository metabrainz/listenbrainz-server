import * as React from "react";
import localforage from "localforage";
import { throttle } from "lodash";
import {
  useBrainzPlayerDispatch,
  useBrainzPlayerContext,
} from "./BrainzPlayerContext";

const brainzplayer_cache = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "brainzplayer",
});
const BP_VOLUME_STORAGE_KEY = "brainzplayer-volume";

function VolumeControlButton() {
  const dispatch = useBrainzPlayerDispatch();
  const { isActivated } = useBrainzPlayerContext();
  const [volume, setVolume] = React.useState(100);

  React.useEffect(() => {
    const loadVolume = async () => {
      try {
        const savedVolume = await brainzplayer_cache.getItem(
          BP_VOLUME_STORAGE_KEY
        );
        if (savedVolume !== null) {
          setVolume(Number(savedVolume));
        }
      } catch (error) {
        console.error("Failed to load volume:", error);
      }
    };
    loadVolume();
  }, []);

  React.useEffect(() => {
    if (isActivated) {
      dispatch({ type: "VOLUME_CHANGE", data: volume });
    }
  }, [isActivated, volume, dispatch]);

  const throttledSaveVolume = React.useMemo(
    () =>
      throttle((v: number) => {
        brainzplayer_cache.setItem(BP_VOLUME_STORAGE_KEY, v).catch((err) => {
          console.error("Failed to save volume:", err);
        });
      }, 1000),
    []
  );

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = Number(e.target.value);
    setVolume(newVolume);
    throttledSaveVolume(newVolume);
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
