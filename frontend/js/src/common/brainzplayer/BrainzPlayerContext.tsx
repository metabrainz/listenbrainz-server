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
  isActivated: false,
  durationMs: 0,
  progressMs: 0,
  updateTime: performance.now(),
  listenSubmitted: false,
  continuousPlaybackTime: 0,
};

function valueReducer(
  state: BrainzPlayerContextT,
  action: Partial<BrainzPlayerContextT>
): BrainzPlayerContextT {
  return { ...state, ...action };
}

const useReduceerWithCallback = (
  reducer: React.Reducer<BrainzPlayerContextT, Partial<BrainzPlayerContextT>>,
  initialState: BrainzPlayerContextT
): [
  BrainzPlayerContextT,
  (action: Partial<BrainzPlayerContextT>, callback?: () => void) => void
] => {
  const [state, dispatch] = React.useReducer(reducer, initialState);

  const callbackRef = React.useRef<() => void>();
  const dispatchWithCallback = (
    action: Partial<BrainzPlayerContextT>,
    callback?: () => void
  ) => {
    dispatch(action);
    if (callback) {
      callbackRef.current = callback;
    }
  };

  React.useEffect(() => {
    if (callbackRef.current) {
      callbackRef.current();
      callbackRef.current = undefined;
    }
  }, [state]);

  return [state, dispatchWithCallback];
};

export const BrainzPlayerContext = React.createContext<BrainzPlayerContextT>(
  initialValue
);
export const BrainzPlayerDispatchContext = React.createContext<
  (action: Partial<BrainzPlayerContextT>, callback?: () => void) => void
>(() => {});

export function BrainzPlayerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [value, dispatch] = useReduceerWithCallback(valueReducer, initialValue);

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
