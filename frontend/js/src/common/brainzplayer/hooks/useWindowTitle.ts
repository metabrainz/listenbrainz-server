import * as React from "react";
import { useAtomValue, useStore } from "jotai";
import { playerPausedAtom, currentTrackNameAtom } from "../BrainzPlayerAtoms";

/**
 * This hook is used to manage the window title for the BrainzPlayer.
 */
export default function useWindowTitle() {
  const store = useStore();
  const playerPaused = useAtomValue(playerPausedAtom);

  const [htmlTitle, setHtmlTitle] = React.useState<string>(
    window.document.title
  );
  const [currentHTMLTitle, setCurrentHTMLTitle] = React.useState<string | null>(
    null
  );

  const getCurrentTrackName = () => store.get(currentTrackNameAtom);

  const updateWindowTitleWithTrackName = React.useCallback(() => {
    const trackName = getCurrentTrackName() || "";
    setCurrentHTMLTitle(`🎵 ${trackName}`);
  }, [getCurrentTrackName]);

  const reinitializeWindowTitle = React.useCallback(() => {
    setCurrentHTMLTitle(htmlTitle);
  }, [htmlTitle]);

  // Update title when track changes or playback state changes
  React.useEffect(() => {
    if (!playerPaused) {
      updateWindowTitleWithTrackName();
    } else {
      reinitializeWindowTitle();
    }
  }, [playerPaused, updateWindowTitleWithTrackName, reinitializeWindowTitle]);

  return {
    htmlTitle,
    setHtmlTitle,
    currentHTMLTitle,
    updateWindowTitleWithTrackName,
    reinitializeWindowTitle,
  };
}
