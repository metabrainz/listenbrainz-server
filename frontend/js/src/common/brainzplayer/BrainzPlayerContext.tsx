import * as React from "react";
import { listenOrJSPFTrackToQueueItem } from "./utils";

export type BrainzPlayerContextT = {
  currentListenIndex: number;
  queue: BrainzPlayerQueue;
  ambientQueue: BrainzPlayerQueue;
};

export const initialValue: BrainzPlayerContextT = {
  currentListenIndex: -1,
  queue: [],
  ambientQueue: [],
};

export type BrainzPlayerActionType = Partial<BrainzPlayerContextT> & {
  type?:
    | "CLEAR_QUEUE_AFTER_CURRENT_AND_SET_AMBIENT_QUEUE"
    | "ADD_LISTEN_TO_TOP_OF_QUEUE"
    | "ADD_LISTEN_TO_BOTTOM_OF_QUEUE";
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
    default: {
      throw Error(`Unknown action: ${action.type}`);
    }
  }
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
