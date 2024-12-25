/* eslint-disable no-console */
import localforage from "localforage";

// Initialize IndexedDB
const coverArtCache = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "coverart",
});

const coverArtCacheExpiry = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "coverart-expiry",
});

const DEFAULT_CACHE_TTL = 1000 * 60 * 60 * 24 * 7; // 7 days

/**
 * Removes all expired entries from both the cover art cache and expiry cache
 * This helps keep the cache size manageable by cleaning up old entries
 */
const removeAllExpiredCacheEntries = async () => {
  try {
    const keys = await coverArtCacheExpiry.keys();
    // Check each key to see if it's expired2
    const expiredKeys = await Promise.all(
      keys.map(async (key) => {
        try {
          const expiry = await coverArtCacheExpiry.getItem<number>(key);
          return expiry && expiry < Date.now() ? key : null;
        } catch {
          // If we can't read the expiry time, treat the entry as expired
          return key;
        }
      })
    );

    // Filter out null values and remove expired entries from both caches
    const keysToRemove = expiredKeys.filter(
      (key): key is string => key !== null
    );
    await Promise.allSettled([
      ...keysToRemove.map((key) => coverArtCache.removeItem(key)),
      ...keysToRemove.map((key) => coverArtCacheExpiry.removeItem(key)),
    ]);
  } catch (error) {
    console.error("Error removing expired cache entries:", error);
  }
};

/**
 * Stores a cover art URL in the cache with an expiration time
 * @param key - Unique identifier for the cover art
 * @param value - The URL or data URI of the cover art
 */
const setCoverArtCache = async (key: string, value: string) => {
  // Validate inputs to prevent storing invalid data
  if (!key || !value) {
    console.error("Invalid key or value provided to setCoverArtCache");
    return;
  }

  try {
    // Store both the cover art and its expiration time simultaneously
    await Promise.allSettled([
      coverArtCache.setItem(key, value),
      coverArtCacheExpiry.setItem(key, Date.now() + DEFAULT_CACHE_TTL),
    ]);
    // Run cleanup in background to avoid blocking the main operation
    removeAllExpiredCacheEntries().catch(console.error);
  } catch (error) {
    console.error("Error setting cover art cache:", error);
  }
};

/**
 * Retrieves a cover art URL from the cache if it exists and hasn't expired
 * @param key - Unique identifier for the cover art
 * @returns The cached cover art URL/data URI, or null if not found/expired
 */
const getCoverArtCache = async (key: string): Promise<string | null> => {
  if (!key) {
    console.error("Invalid key provided to getCoverArtCache");
    return null;
  }

  try {
    // Check if the entry has expired
    const expiry = await coverArtCacheExpiry.getItem<number>(key);
    if (!expiry || expiry < Date.now()) {
      await Promise.allSettled([
        coverArtCache.removeItem(key),
        coverArtCacheExpiry.removeItem(key),
      ]);
      return null;
    }
    return await coverArtCache.getItem<string>(key);
  } catch (error) {
    console.error("Error getting cover art cache:", error);
    return null;
  }
};

export { setCoverArtCache, getCoverArtCache };
