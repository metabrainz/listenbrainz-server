/*
 * listenStorage is the offline retry queue: useListenSubmission calls
 * saveFailedListen when a submission fails, then getFailedListens and
 * removeFailedListen when it retries. Two things therefore matter beyond the
 * plumbing — that two listens are never stored under the same key, and that
 * they come back in the order they were played.
 */

const store = {
  setItem: jest.fn().mockResolvedValue(undefined),
  removeItem: jest.fn().mockResolvedValue(undefined),
  clear: jest.fn().mockResolvedValue(undefined),
  iterate: jest.fn().mockResolvedValue(undefined),
};

jest.mock("localforage", () => ({
  __esModule: true,
  default: { createInstance: jest.fn(() => store) },
}));

// eslint-disable-next-line import/first
import {
  clearFailedListens,
  getFailedListens,
  removeFailedListen,
  saveFailedListen,
} from "../../src/utils/listenStorage";

const listenAt = (listened_at: number, track_name = "t"): Listen =>
  ({ listened_at, track_metadata: { artist_name: "a", track_name } } as Listen);

describe("listenStorage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("saveFailedListen", () => {
    it("keys the entry by when the track was played", async () => {
      await saveFailedListen(listenAt(1605927742));

      const [key, value] = store.setItem.mock.calls[0];
      expect(key).toMatch(/^1605927742-/);
      expect(value).toEqual(listenAt(1605927742));
    });

    it("gives two listens played in the same second distinct keys", async () => {
      // Without the random suffix the second save would overwrite the first
      // and a listen would be silently dropped from the retry queue.
      await saveFailedListen(listenAt(1605927742, "first"));
      await saveFailedListen(listenAt(1605927742, "second"));

      const [firstKey] = store.setItem.mock.calls[0];
      const [secondKey] = store.setItem.mock.calls[1];
      expect(firstKey).not.toEqual(secondKey);
    });
  });

  describe("getFailedListens", () => {
    it("returns each entry with the key it is stored under", async () => {
      store.iterate.mockImplementation(async (fn: any) => {
        fn(listenAt(200), "key-b");
        fn(listenAt(100), "key-a");
      });

      const result = await getFailedListens();

      expect(result).toHaveLength(2);
      expect(result.map((r) => r.id)).toEqual(["key-a", "key-b"]);
    });

    it("orders them by when they were played, not by key order", async () => {
      // The queue is replayed in this order, so it has to be chronological
      // regardless of how the store happens to enumerate.
      store.iterate.mockImplementation(async (fn: any) => {
        fn(listenAt(300), "c");
        fn(listenAt(100), "a");
        fn(listenAt(200), "b");
      });

      const result = await getFailedListens();

      expect(result.map((r) => r.listen.listened_at)).toEqual([100, 200, 300]);
    });

    it("returns an empty list when nothing is queued", async () => {
      store.iterate.mockImplementation(async () => {});

      await expect(getFailedListens()).resolves.toEqual([]);
    });
  });

  describe("removeFailedListen and clearFailedListens", () => {
    it("removes a single entry by its key", async () => {
      await removeFailedListen("key-a");

      expect(store.removeItem).toHaveBeenCalledWith("key-a");
      expect(store.clear).not.toHaveBeenCalled();
    });

    it("clears the whole queue", async () => {
      await clearFailedListens();

      expect(store.clear).toHaveBeenCalled();
      expect(store.removeItem).not.toHaveBeenCalled();
    });
  });
});
