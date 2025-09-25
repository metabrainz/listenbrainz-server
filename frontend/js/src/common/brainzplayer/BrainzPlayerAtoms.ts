import { atom, getDefaultStore, useAtom } from "jotai";
import { atomWithReset, atomWithStorage } from "jotai/utils";
import { faRepeat } from "@fortawesome/free-solid-svg-icons";
import { isEqual } from "lodash";
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
export const store = getDefaultStore();

export const currentListenAtom = atomWithReset<
  BrainzPlayerQueueItem | undefined
>(undefined);
export const currentListenIndexAtom = atomWithReset<number>(-1);
export const currentDataSourceIndexAtom = atomWithReset<number>(0);
export const currentDataSourceNameAtom = atomWithReset<string>("");
export const currentTrackNameAtom = atomWithReset<string>("");
export const currentTrackArtistAtom = atomWithReset<string | undefined>("");
export const currentTrackAlbumAtom = atomWithReset<string | undefined>(
  undefined
);
export const currentTrackURLAtom = atomWithReset<string | undefined>(undefined);
export const currentTrackCoverURLAtom = atomWithReset<string | undefined>(
  undefined
);
export const isActivatedAtom = atomWithReset<boolean>(false);
export const playerPausedAtom = atomWithReset<boolean>(true);
export const volumeAtom = atomWithStorage<number>("brainzplayer-volume", 100);
export const durationMsAtom = atomWithReset<number>(0);
export const progressMsAtom = atomWithReset<number>(0);
export const updateTimeAtom = atomWithReset<number>(performance.now());
export const listenSubmittedAtom = atomWithReset<boolean>(false);
export const continuousPlaybackTimeAtom = atomWithReset<number>(0);
export const queueAtom = atomWithReset<BrainzPlayerQueue>([]);
export const ambientQueueAtom = atomWithReset<BrainzPlayerQueue>([]);
export const queueRepeatModeAtom = atomWithReset<QueueRepeatMode>(
  QueueRepeatModes.off
);

// Action Atoms
export const setAmbientQueueAtom = atom(
  null,
  (get, set, data: Listen[] | JSPFTrack[]) => {
    if (data && data.length > 0) {
      const newQueue = [...data].map(listenOrJSPFTrackToQueueItem);
      set(ambientQueueAtom, newQueue);
    }
  }
);

export const setPlaybackTimerAtom = atom(null, (get, set) => {
  const playerPaused = get(playerPausedAtom);
  const progressMs = get(progressMsAtom);
  const updateTime = get(updateTimeAtom);
  const durationMs = get(durationMsAtom);
  const continuousPlaybackTime = get(continuousPlaybackTimeAtom);

  let newProgressMs: number;
  let elapsedTimeSinceLastUpdate: number;

  if (playerPaused) {
    newProgressMs = progressMs || 0;
    elapsedTimeSinceLastUpdate = 0;
  } else {
    elapsedTimeSinceLastUpdate = performance.now() - updateTime;
    const position = progressMs + elapsedTimeSinceLastUpdate;
    newProgressMs =
      Boolean(durationMs) && position > durationMs ? durationMs : position;
  }

  set(progressMsAtom, newProgressMs);
  set(updateTimeAtom, performance.now());
  set(
    continuousPlaybackTimeAtom,
    continuousPlaybackTime + elapsedTimeSinceLastUpdate
  );
});

export const toggleRepeatModeAtom = atom(null, (get, set) => {
  const queueRepeatMode = get(queueRepeatModeAtom);
  const repeatMode = repeatModes.find((mode) => isEqual(mode, queueRepeatMode));
  const currentIndex = repeatModes.indexOf(repeatMode!);
  const nextIndex = (currentIndex + 1) % repeatModes.length;
  set(queueRepeatModeAtom, repeatModes[nextIndex]);
});

export const moveQueueItemAtom = atom(
  null,
  (get, set, evt: { oldIndex: number; newIndex: number }) => {
    const queue = get(queueAtom);
    const currentListenIndex = get(currentListenIndexAtom);

    const newQueue = [...queue];
    const newIndex = evt.newIndex + currentListenIndex + 1;
    const oldIndex = evt.oldIndex + currentListenIndex + 1;

    const toMove = newQueue[oldIndex];
    newQueue.splice(oldIndex, 1);
    newQueue.splice(newIndex, 0, toMove);

    let newCurrentListenIndex = currentListenIndex;

    if (oldIndex === currentListenIndex) {
      newCurrentListenIndex = newIndex;
    } else if (
      oldIndex < currentListenIndex &&
      newIndex >= currentListenIndex
    ) {
      newCurrentListenIndex -= 1;
    } else if (
      oldIndex > currentListenIndex &&
      newIndex <= currentListenIndex
    ) {
      newCurrentListenIndex += 1;
    }

    set(queueAtom, newQueue);
    set(currentListenIndexAtom, newCurrentListenIndex);
  }
);

export const moveAmbientQueueItemAtom = atom(
  null,
  (get, set, evt: { oldIndex: number; newIndex: number }) => {
    const ambientQueue = get(ambientQueueAtom);
    const newQueue = [...ambientQueue];
    const toMove = newQueue[evt.oldIndex];
    newQueue.splice(evt.oldIndex, 1);
    newQueue.splice(evt.newIndex, 0, toMove);
    set(ambientQueueAtom, newQueue);
  }
);

export const removeTrackFromQueueAtom = atom(
  null,
  (
    get,
    set,
    { track, index }: { track: BrainzPlayerQueueItem; index: number }
  ) => {
    const queue = get(queueAtom);
    const currentListenIndex = get(currentListenIndexAtom);

    if (index < 0 || index >= queue.length || queue[index].id !== track.id) {
      return;
    }

    const updatedQueue = [...queue];
    updatedQueue.splice(index, 1);

    let newCurrentListenIndex = currentListenIndex;
    if (index < currentListenIndex) {
      newCurrentListenIndex -= 1;
    }

    set(queueAtom, updatedQueue);
    set(currentListenIndexAtom, newCurrentListenIndex);
  }
);

export const removeTrackFromAmbientQueueAtom = atom(
  null,
  (
    get,
    set,
    { track, index }: { track: Listen | JSPFTrack; index: number }
  ) => {
    const trackToDelete = listenOrJSPFTrackToQueueItem(track);
    const ambientQueue = get(ambientQueueAtom);

    if (index === -1) {
      const updatedQueue = ambientQueue.filter(
        (trackInQueue) => trackInQueue.id !== trackToDelete.id
      );
      set(ambientQueueAtom, updatedQueue);
      return;
    }

    if (
      index >= ambientQueue.length ||
      ambientQueue[index]?.id !== trackToDelete.id
    ) {
      return;
    }

    const updatedAmbientQueue = [...ambientQueue];
    updatedAmbientQueue.splice(index, 1);
    set(ambientQueueAtom, updatedAmbientQueue);
  }
);

export const addListenToTopOfQueueAtom = atom(
  null,
  (get, set, trackData: any) => {
    const trackToAdd = listenOrJSPFTrackToQueueItem(trackData);
    const queue = get(queueAtom);
    const currentListenIndex = get(currentListenIndexAtom);
    const insertionIndex =
      currentListenIndex === -1 ? 0 : currentListenIndex + 1;

    const updatedQueue = [...queue];
    updatedQueue.splice(insertionIndex, 0, trackToAdd);
    set(queueAtom, updatedQueue);
  }
);

export const addListenToBottomOfQueueAtom = atom(
  null,
  (get, set, trackData: any) => {
    const trackToAdd = listenOrJSPFTrackToQueueItem(trackData);
    const queue = get(queueAtom);
    set(queueAtom, [...queue, trackToAdd]);
  }
);

export const addListenToBottomOfAmbientQueueAtom = atom(
  null,
  (get, set, trackData: any) => {
    const trackToAdd = listenOrJSPFTrackToQueueItem(trackData);
    const ambientQueue = get(ambientQueueAtom);
    set(ambientQueueAtom, [...ambientQueue, trackToAdd]);
  }
);

export const clearQueueAfterCurrentAndSetAmbientQueueAtom = atom(
  null,
  (get, set, data: BrainzPlayerQueue) => {
    const currentListenIndex = get(currentListenIndexAtom);
    const queue = get(queueAtom);
    const updatedQueue = queue.slice(0, currentListenIndex + 1);
    const newAmbientQueue = [...data].map(listenOrJSPFTrackToQueueItem);

    set(queueAtom, updatedQueue);
    set(ambientQueueAtom, newAmbientQueue);
  }
);

export const moveAmbientQueueItemsToQueueAtom = atom(null, (get, set) => {
  const queue = get(queueAtom);
  const ambientQueue = get(ambientQueueAtom);

  set(queueAtom, [...queue, ...ambientQueue]);
  set(ambientQueueAtom, []);
});

export const addMultipleListenToBottomOfAmbientQueueAtom = atom(
  null,
  (get, set, tracksData: BrainzPlayerQueue) => {
    const tracksToAdd = tracksData.map(listenOrJSPFTrackToQueueItem);
    const ambientQueue = get(ambientQueueAtom);
    set(ambientQueueAtom, [...ambientQueue, ...tracksToAdd]);
  }
);

// Derived atoms for computed values
export const currentTrackAtom = atom((get) => {
  const queue = get(queueAtom);
  const currentListenIndex = get(currentListenIndexAtom);
  return currentListenIndex >= 0 && currentListenIndex < queue.length
    ? queue[currentListenIndex]
    : null;
});

export const hasNextTrackAtom = atom((get) => {
  const queue = get(queueAtom);
  const currentListenIndex = get(currentListenIndexAtom);
  const ambientQueue = get(ambientQueueAtom);
  return currentListenIndex < queue.length - 1 || ambientQueue.length > 0;
});

export const hasPreviousTrackAtom = atom((get) => {
  const currentListenIndex = get(currentListenIndexAtom);
  return currentListenIndex > 0;
});

// Convenience hooks for React components
export const useBrainzPlayerAtoms = () => ({
  // State atoms
  ambientQueueAtom,
  queueAtom,
  currentListenIndexAtom,
  playerPausedAtom,
  progressMsAtom,
  updateTimeAtom,
  durationMsAtom,
  continuousPlaybackTimeAtom,
  volumeAtom,
  queueRepeatModeAtom,

  // Action atoms
  setAmbientQueueAtom,
  setPlaybackTimerAtom,
  toggleRepeatModeAtom,
  moveQueueItemAtom,
  moveAmbientQueueItemAtom,
  removeTrackFromQueueAtom,
  removeTrackFromAmbientQueueAtom,
  addListenToTopOfQueueAtom,
  addListenToBottomOfQueueAtom,
  addListenToBottomOfAmbientQueueAtom,
  clearQueueAfterCurrentAndSetAmbientQueueAtom,
  moveAmbientQueueItemsToQueueAtom,
  addMultipleListenToBottomOfAmbientQueueAtom,

  // Derived atoms
  currentTrackAtom,
  hasNextTrackAtom,
  hasPreviousTrackAtom,
});
