import * as React from "react";
import { faRepeat } from "@fortawesome/free-solid-svg-icons";
import { isEqual, isNil } from "lodash";
import { faRepeatOnce } from "../../utils/icons";
import { listenOrJSPFTrackToQueueItem } from "./utils";

export const QueueRepeatModes = {
  off: {
    icon: faRepeatOnce,
    title: "Repeat off",
    color: undefined,
  },
  one: {
    icon: faRepeatOnce,
    title: "Repeat one",
    color: "green",
  },
  all: {
    icon: faRepeat,
    title: "Repeat all",
    color: "green",
  },
} as const;

export type QueueRepeatMode = typeof QueueRepeatModes[keyof typeof QueueRepeatModes];

const repeatModes = [
  QueueRepeatModes.off,
  QueueRepeatModes.all,
  QueueRepeatModes.one,
];

export type BrainzPlayerContextT = {
  currentListen?: BrainzPlayerQueueItem;
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
  queue: BrainzPlayerQueue;
  ambientQueue: BrainzPlayerQueue;
  queueRepeatMode: QueueRepeatMode;
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
  queue: [],
  ambientQueue: [],
  queueRepeatMode: QueueRepeatModes.off,
};

export type BrainzPlayerActionType = Partial<BrainzPlayerContextT> & {
  type?:
    | "SET_CURRENT_LISTEN"
    | "SET_PLAYBACK_TIMER"
    | "TOGGLE_REPEAT_MODE"
    | "MOVE_QUEUE_ITEM"
    | "MOVE_AMBIENT_QUEUE_ITEM"
    | "REMOVE_TRACK_FROM_QUEUE"
    | "REMOVE_TRACK_FROM_AMBIENT_QUEUE"
    | "ADD_LISTEN_TO_TOP_OF_QUEUE"
    | "ADD_LISTEN_TO_BOTTOM_OF_QUEUE"
    | "ADD_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE";
  data?: any;
};

function valueReducer(
  state: BrainzPlayerContextT,
  action: BrainzPlayerActionType
): BrainzPlayerContextT {
  if (!action.type) {
    return { ...state, ...action };
  }

  const isCurrentlyPlaying = (element: BrainzPlayerQueueItem) => {
    const { currentListen } = state;
    if (isNil(currentListen)) {
      return false;
    }

    return isEqual(element.id, currentListen.id);
  };

  switch (action.type) {
    case "SET_CURRENT_LISTEN": {
      if (!action.data) {
        return { ...state, ...action };
      }
      const data = action.data as BrainzPlayerQueue;
      const { type, data: _, ...restActions } = action;
      const newQueue = [...data].map(listenOrJSPFTrackToQueueItem);
      if (data.length !== 0) {
        return {
          ...state,
          ...restActions,
          ambientQueue: newQueue,
        };
      }
      break;
    }
    case "SET_PLAYBACK_TIMER": {
      const { playerPaused, progressMs, updateTime, durationMs } = state;
      let newProgressMs: number;
      let elapsedTimeSinceLastUpdate: number;
      if (playerPaused) {
        newProgressMs = progressMs || 0;
        elapsedTimeSinceLastUpdate = 0;
      } else {
        elapsedTimeSinceLastUpdate = performance.now() - updateTime;
        const position = progressMs + elapsedTimeSinceLastUpdate;
        newProgressMs = position > durationMs ? durationMs : position;
      }
      return {
        ...state,
        progressMs: newProgressMs,
        updateTime: performance.now(),
        continuousPlaybackTime:
          state.continuousPlaybackTime + elapsedTimeSinceLastUpdate,
      };
    }
    case "TOGGLE_REPEAT_MODE": {
      const { queueRepeatMode } = state;
      const repeatMode = repeatModes.find((mode) =>
        isEqual(mode, queueRepeatMode)
      );
      const currentIndex = repeatModes.indexOf(repeatMode!);
      const nextIndex = (currentIndex + 1) % repeatModes.length;
      return {
        ...state,
        queueRepeatMode: repeatModes[nextIndex],
      };
    }
    case "MOVE_QUEUE_ITEM": {
      const { queue } = state;
      const evt = action.data as any;
      const currentListenIndex = queue.findIndex(isCurrentlyPlaying);

      const newQueue = [...queue];
      const newIndex = evt.newIndex + currentListenIndex;
      const oldIndex = evt.oldIndex + currentListenIndex;

      const toMove = newQueue[newIndex];
      newQueue[newIndex] = newQueue[oldIndex];
      newQueue[oldIndex] = toMove;

      return {
        ...state,
        queue: newQueue,
      };
    }
    case "MOVE_AMBIENT_QUEUE_ITEM": {
      const { ambientQueue } = state;
      const evt = action.data as any;

      const newQueue = [...ambientQueue];
      const toMove = newQueue[evt.newIndex];
      newQueue[evt.newIndex] = newQueue[evt.oldIndex];
      newQueue[evt.oldIndex] = toMove;

      return {
        ...state,
        ambientQueue: newQueue,
      };
    }
    case "REMOVE_TRACK_FROM_QUEUE": {
      const trackToDelete = action.data as BrainzPlayerQueueItem;
      const { queue } = state;
      const updatedQueue = queue.filter(
        (track) => track.id !== trackToDelete.id
      );
      return {
        ...state,
        queue: updatedQueue,
      };
    }
    case "REMOVE_TRACK_FROM_AMBIENT_QUEUE": {
      const trackToDelete = action.data as BrainzPlayerQueueItem;
      const { ambientQueue } = state;
      const updatedQueue = ambientQueue.filter(
        (track) => track.id !== trackToDelete.id
      );
      return {
        ...state,
        ambientQueue: updatedQueue,
      };
    }
    case "ADD_LISTEN_TO_TOP_OF_QUEUE": {
      const trackToAdd = listenOrJSPFTrackToQueueItem(action.data);
      const { queue } = state;
      const currentListenIndex = queue.findIndex(isCurrentlyPlaying);
      const insertionIndex =
        currentListenIndex === -1 ? 0 : currentListenIndex + 1;

      const updatedQueue = [...queue];
      updatedQueue.splice(insertionIndex, 0, trackToAdd);

      return {
        ...state,
        queue: updatedQueue,
      };
    }
    case "ADD_LISTEN_TO_BOTTOM_OF_QUEUE": {
      const trackToAdd = listenOrJSPFTrackToQueueItem(action.data);
      const { queue } = state;
      return {
        ...state,
        queue: [...queue, trackToAdd],
      };
    }
    case "ADD_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE": {
      const trackToAdd = listenOrJSPFTrackToQueueItem(action.data);
      const { ambientQueue } = state;
      return {
        ...state,
        ambientQueue: [...ambientQueue, trackToAdd],
      };
    }
    default: {
      throw Error(`Unknown action: ${action.type}`);
    }
  }
  return state;
}

const useReducerWithCallback = (
  reducer: React.Reducer<BrainzPlayerContextT, BrainzPlayerActionType>,
  initialState: BrainzPlayerContextT
): [
  BrainzPlayerContextT,
  (action: BrainzPlayerActionType, callback?: () => void) => void
] => {
  const [state, dispatch] = React.useReducer(reducer, initialState);

  const callbacksStackRef = React.useRef<(() => void)[]>([]);
  const dispatchWithCallback = (
    action: BrainzPlayerActionType,
    callback?: () => void
  ) => {
    dispatch(action);
    if (callback) {
      callbacksStackRef.current.push(callback);
    }
  };

  React.useEffect(() => {
    const executeCallback = () => {
      const callback = callbacksStackRef.current.pop();
      if (callback) {
        callback();
        executeCallback();
      }
    };

    executeCallback();
  }, [state]);

  return [state, dispatchWithCallback];
};

export const BrainzPlayerContext = React.createContext<BrainzPlayerContextT>(
  initialValue
);
export const BrainzPlayerDispatchContext = React.createContext<
  (action: BrainzPlayerActionType, callback?: () => void) => void
>(() => {});

export function BrainzPlayerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [value, dispatch] = useReducerWithCallback(valueReducer, initialValue);

  const memoizedValue = React.useMemo(() => value, [value]);
  const memoizedDispatch = React.useMemo(() => dispatch, []);

  return (
    <BrainzPlayerContext.Provider value={memoizedValue}>
      <BrainzPlayerDispatchContext.Provider value={memoizedDispatch}>
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
