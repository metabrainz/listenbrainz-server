import * as React from "react";

export type BrainzPlayerContextT = {
  currentListen?: Listen | JSPFTrack;
  currentDataSourceIndex: number;
  currentTrackName: string;
  currentTrackArtist?: string;
  currentTrackAlbum?: string;
  currentTrackURL?: string;
  playerPaused: boolean;
  isActivated: boolean;
  durationMs: number;
  progressMs: number;
  updateTime: number;
  listenSubmitted: boolean;
  continuousPlaybackTime: number;
};

const initialValue: BrainzPlayerContextT = {
  currentDataSourceIndex: 0,
  currentTrackName: "",
  currentTrackArtist: "",
  playerPaused: true,
  progressMs: 0,
  durationMs: 0,
  updateTime: performance.now(),
  continuousPlaybackTime: 0,
  isActivated: false,
  listenSubmitted: false,
};

function valueReducer(
  state: BrainzPlayerContextT,
  action: Partial<BrainzPlayerContextT>
): BrainzPlayerContextT {
  return { ...state, ...action };
}

export const BrainzPlayerContext = React.createContext<BrainzPlayerContextT>(
  initialValue
);
export const BrainzPlayerDispatchContext = React.createContext<
  React.Dispatch<Partial<BrainzPlayerContextT>>
>(() => {});

export function BrainzPlayerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [value, dispatch] = React.useReducer(valueReducer, initialValue);

  return (
    <BrainzPlayerContext.Provider value={value}>
      <BrainzPlayerDispatchContext.Provider value={dispatch}>
        {children}
      </BrainzPlayerDispatchContext.Provider>
    </BrainzPlayerContext.Provider>
  );
}

export function useBrainzPlayerContext() {
  return React.useContext(BrainzPlayerContext);
}

export function useBrainzPlayerDispatch() {
  return React.useContext(BrainzPlayerDispatchContext);
}
