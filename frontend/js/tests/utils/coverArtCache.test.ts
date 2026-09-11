/*
 * coverArtCache keeps two localforage stores in step: the artwork itself and a
 * parallel expiry timestamp. The pairing is the whole point of the module, so
 * these tests drive both stores and assert they stay consistent.
 */

// Two instances are created at module load — artwork first, expiry second —
// so they are captured in that order and handed back to the tests.
const instances: Array<Record<string, jest.Mock>> = [];
const makeInstance = () => {
  const inst = {
    setItem: jest.fn().mockResolvedValue(undefined),
    getItem: jest.fn().mockResolvedValue(null),
    removeItem: jest.fn().mockResolvedValue(undefined),
    keys: jest.fn().mockResolvedValue([]),
  };
  instances.push(inst);
  return inst;
};

jest.mock("localforage", () => ({
  __esModule: true,
  default: {
    createInstance: jest.fn(() => makeInstance()),
    INDEXEDDB: "indexeddb",
    LOCALSTORAGE: "localstorage",
  },
}));

// eslint-disable-next-line import/first
import {
  setCoverArtCache,
  getCoverArtCache,
} from "../../src/utils/coverArtCache";

const [artStore, expiryStore] = instances;
const SEVEN_DAYS = 1000 * 60 * 60 * 24 * 7;

describe("coverArtCache", () => {
  let consoleError: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    artStore.getItem.mockResolvedValue(null);
    expiryStore.getItem.mockResolvedValue(null);
    expiryStore.keys.mockResolvedValue([]);
    consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  describe("setCoverArtCache", () => {
    it("writes the artwork and an expiry together", async () => {
      const now = 1_700_000_000_000;
      jest.spyOn(Date, "now").mockReturnValue(now);

      await setCoverArtCache("mbid-1", "https://example.test/art.jpg");

      expect(artStore.setItem).toHaveBeenCalledWith(
        "mbid-1",
        "https://example.test/art.jpg"
      );
      expect(expiryStore.setItem).toHaveBeenCalledWith(
        "mbid-1",
        now + SEVEN_DAYS
      );
    });

    it.each([
      ["an empty key", "", "url"],
      ["an empty value", "key", ""],
    ])("writes nothing for %s", async (_label, key, value) => {
      await setCoverArtCache(key, value);

      expect(artStore.setItem).not.toHaveBeenCalled();
      expect(expiryStore.setItem).not.toHaveBeenCalled();
      expect(consoleError).toHaveBeenCalled();
    });
  });

  describe("getCoverArtCache", () => {
    it("returns the artwork while the entry is live", async () => {
      expiryStore.getItem.mockResolvedValue(Date.now() + SEVEN_DAYS);
      artStore.getItem.mockResolvedValue("https://example.test/art.jpg");

      await expect(getCoverArtCache("mbid-1")).resolves.toBe(
        "https://example.test/art.jpg"
      );
      expect(artStore.removeItem).not.toHaveBeenCalled();
    });

    it("drops an expired entry from both stores and returns null", async () => {
      expiryStore.getItem.mockResolvedValue(Date.now() - 1000);

      await expect(getCoverArtCache("mbid-1")).resolves.toBeNull();
      expect(artStore.removeItem).toHaveBeenCalledWith("mbid-1");
      expect(expiryStore.removeItem).toHaveBeenCalledWith("mbid-1");
      // The artwork must not be read once the entry is known to be stale.
      expect(artStore.getItem).not.toHaveBeenCalled();
    });

    it("treats a missing expiry as expired rather than as live forever", async () => {
      // An artwork entry whose expiry half never landed would otherwise
      // never be evicted.
      expiryStore.getItem.mockResolvedValue(null);

      await expect(getCoverArtCache("mbid-1")).resolves.toBeNull();
      expect(artStore.removeItem).toHaveBeenCalledWith("mbid-1");
    });

    it("returns null for an empty key without touching the stores", async () => {
      await expect(getCoverArtCache("")).resolves.toBeNull();

      expect(expiryStore.getItem).not.toHaveBeenCalled();
      expect(artStore.getItem).not.toHaveBeenCalled();
      expect(consoleError).toHaveBeenCalled();
    });

    it("returns null instead of throwing when the store fails", async () => {
      expiryStore.getItem.mockRejectedValue(new Error("IndexedDB unavailable"));

      await expect(getCoverArtCache("mbid-1")).resolves.toBeNull();
      expect(consoleError).toHaveBeenCalled();
    });
  });

  describe("expiry sweep", () => {
    it("removes only the expired keys from both stores", async () => {
      const now = 1_700_000_000_000;
      jest.spyOn(Date, "now").mockReturnValue(now);
      expiryStore.keys.mockResolvedValue(["stale", "fresh"]);
      expiryStore.getItem.mockImplementation(async (key: string) =>
        key === "stale" ? now - 1 : now + SEVEN_DAYS
      );

      await setCoverArtCache("new", "url");
      // The sweep runs detached from the write, so let it settle.
      await new Promise(process.nextTick);

      expect(artStore.removeItem).toHaveBeenCalledWith("stale");
      expect(expiryStore.removeItem).toHaveBeenCalledWith("stale");
      expect(artStore.removeItem).not.toHaveBeenCalledWith("fresh");
    });

    it("treats an unreadable expiry as expired", async () => {
      expiryStore.keys.mockResolvedValue(["unreadable"]);
      expiryStore.getItem.mockRejectedValue(new Error("read failed"));

      await setCoverArtCache("new", "url");
      await new Promise(process.nextTick);

      expect(artStore.removeItem).toHaveBeenCalledWith("unreadable");
    });
  });
});
