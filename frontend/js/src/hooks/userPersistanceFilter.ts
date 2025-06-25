import { useEffect } from "react";
import localforage from "localforage";

const release_filters_cache = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "fresh-releases",
});
const RELEASE_FILTERS_STORAGE_KEY = "release-filters";

interface StoredFilters {
  checkedList: Array<string | undefined>;
  releaseTagsCheckList: Array<string | undefined>;
  releaseTagsExcludeCheckList: Array<string | undefined>;
  includeVariousArtists: boolean;
  coverartOnly: boolean;
}

interface UseFilterPersistenceParams {
  checkedList: Array<string | undefined>;
  releaseTagsCheckList: Array<string | undefined>;
  releaseTagsExcludeCheckList: Array<string | undefined>;
  includeVariousArtists: boolean;
  coverartOnly: boolean;

  setCheckedList: (list: Array<string | undefined>) => void;
  setReleaseTagsCheckList: (list: Array<string | undefined>) => void;
  setReleaseTagsExcludeCheckList: (list: Array<string | undefined>) => void;
  setIncludeVariousArtists: (value: boolean) => void;
  setCoverartOnly: (value: boolean) => void;
}

export default function useFilterPersistence(
  params: UseFilterPersistenceParams
) {
  const {
    checkedList,
    releaseTagsCheckList,
    releaseTagsExcludeCheckList,
    includeVariousArtists,
    coverartOnly,
    setCheckedList,
    setReleaseTagsCheckList,
    setReleaseTagsExcludeCheckList,
    setIncludeVariousArtists,
    setCoverartOnly,
  } = params;

  // Load filters on component mount
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const savedFilters = await release_filters_cache.getItem<StoredFilters>(
          RELEASE_FILTERS_STORAGE_KEY
        );
        if (savedFilters) {
          setCheckedList(savedFilters.checkedList ?? []);
          setReleaseTagsCheckList(savedFilters.releaseTagsCheckList ?? []);
          setReleaseTagsExcludeCheckList(
            savedFilters.releaseTagsExcludeCheckList ?? []
          );
          setIncludeVariousArtists(savedFilters.includeVariousArtists ?? false);
          setCoverartOnly(savedFilters.coverartOnly ?? false);
        }
      } catch (error) {
        console.error("Failed to load filters:", error);
      }
    };
    loadFilters();
  }, []);

  // Save filters when they change
  useEffect(() => {
    const saveFilters = async () => {
      try {
        const filtersToSave: StoredFilters = {
          checkedList: checkedList.filter(
            (item): item is string => item !== undefined
          ),
          releaseTagsCheckList: releaseTagsCheckList.filter(
            (item): item is string => item !== undefined
          ),
          releaseTagsExcludeCheckList: releaseTagsExcludeCheckList.filter(
            (item): item is string => item !== undefined
          ),
          includeVariousArtists,
          coverartOnly,
        };
        await release_filters_cache.setItem(
          RELEASE_FILTERS_STORAGE_KEY,
          filtersToSave
        );
      } catch (error) {
        console.error("Failed to save filters:", error);
      }
    };
    saveFilters();
  }, [
    checkedList,
    releaseTagsCheckList,
    releaseTagsExcludeCheckList,
    includeVariousArtists,
    coverartOnly,
  ]);

  const clearSavedFilters = async () => {
    try {
      await release_filters_cache.removeItem(RELEASE_FILTERS_STORAGE_KEY);
      setCheckedList([]);
      setReleaseTagsCheckList([]);
      setReleaseTagsExcludeCheckList([]);
      setIncludeVariousArtists(false);
      setCoverartOnly(false);
    } catch (error) {
      console.error("Failed to clear filters:", error);
    }
  };
  return { clearSavedFilters };
}
