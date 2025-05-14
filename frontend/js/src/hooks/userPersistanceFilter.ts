import { useEffect } from "react";
import localforage from "localforage";

const FILTERS_STORAGE_KEY = "releaseFiltersState";

interface StoredFilters {
  checkedList: Array<string | undefined>;
  releaseTagsCheckList: Array<string | undefined>;
  releaseTagsExcludeCheckList: Array<string | undefined>;
  includeVariousArtists: boolean;
  coverartOnly: boolean;
  showPastReleases: boolean;
  showFutureReleases: boolean;
}

interface UseFilterPersistenceParams {
  // State values
  checkedList: Array<string | undefined>;
  releaseTagsCheckList: Array<string | undefined>;
  releaseTagsExcludeCheckList: Array<string | undefined>;
  includeVariousArtists: boolean;
  coverartOnly: boolean;
  showPastReleases: boolean;
  showFutureReleases: boolean;

  // State setters
  setCheckedList: (list: Array<string | undefined>) => void;
  setReleaseTagsCheckList: (list: Array<string | undefined>) => void;
  setReleaseTagsExcludeCheckList: (list: Array<string | undefined>) => void;
  setIncludeVariousArtists: (value: boolean) => void;
  setCoverartOnly: (value: boolean) => void;
  setShowPastReleases?: (value: boolean) => void;
  setShowFutureReleases?: (value: boolean) => void;
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
    showPastReleases,
    showFutureReleases,
    setCheckedList,
    setReleaseTagsCheckList,
    setReleaseTagsExcludeCheckList,
    setIncludeVariousArtists,
    setCoverartOnly,
    setShowPastReleases,
    setShowFutureReleases,
  } = params;

  // Load filters on component mount
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const savedFilters = await localforage.getItem<StoredFilters>(
          FILTERS_STORAGE_KEY
        );
        if (savedFilters) {
          setCheckedList(savedFilters.checkedList ?? []);
          setReleaseTagsCheckList(savedFilters.releaseTagsCheckList ?? []);
          setReleaseTagsExcludeCheckList(
            savedFilters.releaseTagsExcludeCheckList ?? []
          );
          setIncludeVariousArtists(savedFilters.includeVariousArtists ?? false);
          setCoverartOnly(savedFilters.coverartOnly ?? false);

          setShowPastReleases?.(savedFilters.showPastReleases ?? true);
          setShowFutureReleases?.(savedFilters.showFutureReleases ?? true);
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
        // Filter out undefined values before saving
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
          showPastReleases,
          showFutureReleases,
        };
        await localforage.setItem(FILTERS_STORAGE_KEY, filtersToSave);
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
    showPastReleases,
    showFutureReleases,
  ]);

  const clearSavedFilters = async () => {
    try {
      await localforage.removeItem(FILTERS_STORAGE_KEY);
      setCheckedList([]);
      setReleaseTagsCheckList([]);
      setReleaseTagsExcludeCheckList([]);
      setIncludeVariousArtists(false);
      setCoverartOnly(false);
      setShowPastReleases?.(true);
      setShowFutureReleases?.(true);
    } catch (error) {
      console.error("Failed to clear filters:", error);
    }
  };

  return { clearSavedFilters };
}
