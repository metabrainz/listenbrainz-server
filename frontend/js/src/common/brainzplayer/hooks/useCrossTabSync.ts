import * as React from "react";
import { useAtomValue, useStore } from "jotai";
import {
  playerPausedAtom,
  currentDataSourceIndexAtom,
} from "../BrainzPlayerAtoms";

/**
 * This hook is used to handle cross-tab synchronization for the BrainzPlayer.
 */
export default function useCrossTabSync(dataSourceManager: any) {
  const store = useStore();
  const playerPaused = useAtomValue(playerPausedAtom);

  const getCurrentDataSourceIndex = () => store.get(currentDataSourceIndexAtom);

  // Handle incoming storage events from other tabs
  /** We use LocalStorage events as a form of communication between BrainzPlayers
   * that works across browser windows/tabs, to ensure only one BP is playing at a given time.
   * The event is not fired in the tab/window where the localStorage.setItem call initiated.
   */
  const onLocalStorageEvent = React.useCallback(
    async (event: StorageEvent) => {
      if (event.storageArea !== localStorage) return;

      if (event.key === "BrainzPlayer_stop") {
        const dataSource =
          dataSourceManager.dataSourceRefs[getCurrentDataSourceIndex()]
            ?.current;
        if (dataSource && !playerPaused) {
          await dataSource.togglePlay();
        }
      }
    },
    [dataSourceManager, getCurrentDataSourceIndex, playerPaused]
  );

  // Tell other tabs to stop playing
  const stopOtherBrainzPlayers = React.useCallback((): void => {
    // Using timestamp to ensure a new value each time
    window?.localStorage?.setItem("BrainzPlayer_stop", Date.now().toString());
  }, []);

  // Setup and cleanup event listeners
  React.useEffect(() => {
    window.addEventListener("storage", onLocalStorageEvent);

    return () => {
      window.removeEventListener("storage", onLocalStorageEvent);
    };
  }, [onLocalStorageEvent]);

  return {
    stopOtherBrainzPlayers,
  };
}
