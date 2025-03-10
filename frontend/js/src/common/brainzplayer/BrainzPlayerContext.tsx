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
  currentListenIndex: number;
  currentDataSourceIndex: number;
  currentTrackName: string;
  currentTrackArtist?: string;
  currentTrackAlbum?: string;
  currentTrackURL?: string;
  currentTrackCoverURL?: string;
  playerPaused: boolean;
  isActivated: boolean;
  volume: number;
  durationMs: number;
  progressMs: number;
  updateTime: number;
  listenSubmitted: boolean;
  continuousPlaybackTime: number;
  queue: BrainzPlayerQueue;
  ambientQueue: BrainzPlayerQueue;
  queueRepeatMode: QueueRepeatMode;
};

export const initialValue: BrainzPlayerContextT = {
  currentListenIndex: -1,
  currentDataSourceIndex: 0,
  currentTrackName: "",
  currentTrackArtist: "",
  playerPaused: true,
  isActivated: false,
  volume: 100,
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
    | "SET_AMBIENT_QUEUE"
    | "SET_PLAYBACK_TIMER"
    | "TOGGLE_REPEAT_MODE"
    | "MOVE_QUEUE_ITEM"
    | "VOLUME_CHANGE"
    | "CLEAR_QUEUE_AFTER_CURRENT_AND_SET_AMBIENT_QUEUE"
    | "MOVE_AMBIENT_QUEUE_ITEM"
    | "MOVE_AMBIENT_QUEUE_ITEMS_TO_QUEUE"
    | "REMOVE_TRACK_FROM_QUEUE"
    | "REMOVE_TRACK_FROM_AMBIENT_QUEUE"
    | "ADD_LISTEN_TO_TOP_OF_QUEUE"
    | "ADD_LISTEN_TO_BOTTOM_OF_QUEUE"
    | "ADD_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE"
    | "ADD_MULTIPLE_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE";
  data?: any;
};

function valueReducer(
  state: BrainzPlayerContextT,
  action: BrainzPlayerActionType
): BrainzPlayerContextT {
  if (!action.type) {
    return { ...state, ...action };
  }

  switch (action.type) {
    case "SET_AMBIENT_QUEUE": {
      if (!action.data) {
        return { ...state, ...action };
      }
      const data = action.data as BrainzPlayerQueue;
      const { data: _, ...restActions } = action;
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
      const { queue, currentListenIndex } = state;
      const evt = action.data as any;

      const newQueue = [...queue];
      const newIndex = evt.newIndex + currentListenIndex + 1;
      const oldIndex = evt.oldIndex + currentListenIndex + 1;

      const toMove = newQueue[oldIndex];
      newQueue.splice(oldIndex, 1);
      newQueue.splice(newIndex, 0, toMove);

      let newCurrentListenIndex = currentListenIndex;

      if (oldIndex === currentListenIndex) {
        // If the currently playing track is the one being moved
        newCurrentListenIndex = newIndex;
      } else if (
        oldIndex < currentListenIndex &&
        newIndex >= currentListenIndex
      ) {
        // If an item before the current listen is moved to after it
        newCurrentListenIndex -= 1;
      } else if (
        oldIndex > currentListenIndex &&
        newIndex <= currentListenIndex
      ) {
        // If an item after the current listen is moved to before it
        newCurrentListenIndex += 1;
      }

      return {
        ...state,
        queue: newQueue,
        currentListenIndex: newCurrentListenIndex,
      };
    }
    case "VOLUME_CHANGE": {
      return { ...state, volume: action.data };
    }
    case "MOVE_AMBIENT_QUEUE_ITEM": {
      const { ambientQueue } = state;
      const evt = action.data as any;

      const newQueue = [...ambientQueue];
      const toMove = newQueue[evt.oldIndex];
      newQueue.splice(evt.oldIndex, 1);
      newQueue.splice(evt.newIndex, 0, toMove);

      return {
        ...state,
        ambientQueue: newQueue,
      };
    }
    case "REMOVE_TRACK_FROM_QUEUE": {
      const { track: trackToDelete, index } = action.data as {
        track: BrainzPlayerQueueItem;
        index: number;
      };
      const { queue, currentListenIndex = -1 } = state;

      if (
        index < 0 ||
        index >= queue.length ||
        queue[index].id !== trackToDelete.id
      ) {
        return state;
      }

      const updatedQueue = [...queue];
      updatedQueue.splice(index, 1);

      // Calculate the new currentListenIndex
      let newCurrentListenIndex = currentListenIndex;
      if (index < currentListenIndex) {
        newCurrentListenIndex -= 1;
      }

      return {
        ...state,
        queue: updatedQueue,
        currentListenIndex: newCurrentListenIndex,
      };
    }
    case "REMOVE_TRACK_FROM_AMBIENT_QUEUE": {
      const { track, index } = action.data as {
        track: BrainzPlayerQueueItem;
        index: number;
      };
      const trackToDelete = listenOrJSPFTrackToQueueItem(track);
      const { ambientQueue } = state;

      if (index === -1) {
        const updatedQueue = ambientQueue.filter(
          (trackInQueue) => trackInQueue.id !== trackToDelete.id
        );
        return {
          ...state,
          ambientQueue: updatedQueue,
        };
      }

      if (
        index >= ambientQueue.length ||
        ambientQueue[index]?.id !== trackToDelete.id
      ) {
        return state;
      }

      const updatedAmbientQueue = [...ambientQueue];
      updatedAmbientQueue.splice(index, 1);

      return {
        ...state,
        ambientQueue: updatedAmbientQueue,
      };
    }
    case "ADD_LISTEN_TO_TOP_OF_QUEUE": {
      const trackToAdd = listenOrJSPFTrackToQueueItem(action.data);
      const { queue, currentListenIndex } = state;
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
    case "CLEAR_QUEUE_AFTER_CURRENT_AND_SET_AMBIENT_QUEUE": {
      const { currentListenIndex, queue } = state;
      const updatedQueue = queue.slice(0, currentListenIndex + 1);
      const data = action.data as BrainzPlayerQueue;
      const { data: _, ...restActions } = action;
      const newAmbientQueue = [...data].map(listenOrJSPFTrackToQueueItem);
      return {
        ...state,
        ...restActions,
        queue: updatedQueue,
        ambientQueue: newAmbientQueue,
      };
    }
    case "MOVE_AMBIENT_QUEUE_ITEMS_TO_QUEUE": {
      const { queue, ambientQueue } = state;
      return {
        ...state,
        queue: [...queue, ...ambientQueue],
        ambientQueue: [],
      };
    }
    case "ADD_MULTIPLE_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE": {
      const tracksToAdd = (action.data as BrainzPlayerQueue).map(
        listenOrJSPFTrackToQueueItem
      );
      const { ambientQueue } = state;
      return {
        ...state,
        ambientQueue: [...ambientQueue, ...tracksToAdd],
      };
    }
    default: {
      throw Error(`Unknown action: ${action.type}`);
    }
  }
  return state;
}

export const useReducerWithCallback = (
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
  additionalContextValues,
}: {
  children: React.ReactNode;
  additionalContextValues?: Partial<BrainzPlayerContextT>;
}) {
  const [value, dispatch] = useReducerWithCallback(valueReducer, {
    ...initialValue,
    ...additionalContextValues,
  });

  const memoizedValue = React.useMemo(() => value, [value]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
