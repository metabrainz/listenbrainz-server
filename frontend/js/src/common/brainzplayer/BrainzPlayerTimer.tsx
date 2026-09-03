import * as React from "react";
import { useAtomValue } from "jotai";
import { millisecondsToStr } from "../../playlists/utils";

import { progressMsAtom, durationMsAtom } from "./BrainzPlayerAtoms";

export default function BrainzPlayerTimer() {
  const progressMs = useAtomValue(progressMsAtom);
  const durationMs = useAtomValue(durationMsAtom);

  return (
    <div className="elapsed small text-muted">
      {millisecondsToStr(progressMs)}
      &#8239;/&#8239;
      {millisecondsToStr(durationMs)}
    </div>
  );
}
