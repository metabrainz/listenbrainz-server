import { createStore } from "jotai";
import {
  clearQueuesBeforeListenAndSetQueuesAtom,
  currentListenIndexAtom,
  queueAtom,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";
import { listenOrJSPFTrackToQueueItem } from "../../../src/common/brainzplayer/utils";

const makeListen = (trackName: string): Listen => ({
  listened_at: 0,
  track_metadata: { artist_name: "Artist", track_name: trackName },
});

const listenA = makeListen("A");
const listenB = makeListen("B");
const listenC = makeListen("C");

describe("clearQueuesBeforeListenAndSetQueuesAtom", () => {
  let store: ReturnType<typeof createStore>;

  beforeEach(() => {
    store = createStore();
    store.set(
      queueAtom,
      [listenA, listenB, listenC].map(listenOrJSPFTrackToQueueItem)
    );
  });

  // BrainzPlayer plays queue[currentListenIndex + 1] right after this atom runs,
  // so that slot must hold the track that was clicked
  const nextTrackToPlay = () =>
    store.get(queueAtom)[store.get(currentListenIndexAtom) + 1];

  it("plays the clicked track when it is later in the queue", () => {
    store.set(currentListenIndexAtom, 0);
    store.set(clearQueuesBeforeListenAndSetQueuesAtom, listenC);
    expect(nextTrackToPlay()?.track_metadata.track_name).toEqual("C");
  });

  it("plays the clicked track when it is earlier in the queue", () => {
    store.set(currentListenIndexAtom, 2);
    store.set(clearQueuesBeforeListenAndSetQueuesAtom, listenB);
    expect(nextTrackToPlay()?.track_metadata.track_name).toEqual("B");
  });

  it("replays the currently playing track", () => {
    store.set(currentListenIndexAtom, 1);
    store.set(clearQueuesBeforeListenAndSetQueuesAtom, listenB);
    expect(nextTrackToPlay()?.track_metadata.track_name).toEqual("B");
  });
});
