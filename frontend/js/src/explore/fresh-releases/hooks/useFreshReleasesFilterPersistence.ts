import localforage from "localforage";
import * as React from "react";

const filterStore = localforage.createInstance({
  name: "listenbrainz",
  storeName: "fresh-releases-filters",
});

export type FreshReleasesFilters = {
  checkedList: Array<string | undefined>;
  releaseTagsCheckList: Array<string | undefined>;
  releaseTagsExcludeCheckList: Array<string | undefined>;
  includeVariousArtists: boolean;
  coverartOnly: boolean;
};

const DEFAULT_FILTERS: FreshReleasesFilters = {
  checkedList: [],
  releaseTagsCheckList: [],
  releaseTagsExcludeCheckList: [],
  includeVariousArtists: false,
  coverartOnly: false,
};

const getStorageKey = (pageType: string): string =>
  `release-filters-${pageType}`;

export default function useFreshReleasesFilterPersistence(pageType: string) {
  const [freshReleasesFilters, setFreshReleasesFiltersState] = React.useState<
    FreshReleasesFilters
  >(DEFAULT_FILTERS);

  // Load persisted filters for this pageType on mount / when pageType changes
  React.useEffect(() => {
    let isMounted = true;
    const storageKey = getStorageKey(pageType);

    filterStore.getItem<FreshReleasesFilters>(storageKey).then((stored) => {
      if (isMounted && stored) {
        setFreshReleasesFiltersState(stored);
      } else if (isMounted) {
        setFreshReleasesFiltersState(DEFAULT_FILTERS);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [pageType]);

  // Persist filters whenever they change. Kept separate from the state
  // updater below so that the updater stays a pure function (calling the
  // async filterStore.setItem() inside a setState updater is an anti-pattern,
  // since updaters can run more than once, e.g. under React StrictMode).
  React.useEffect(() => {
    const storageKey = getStorageKey(pageType);
    filterStore.setItem(storageKey, freshReleasesFilters);
  }, [pageType, freshReleasesFilters]);

  const setFreshReleasesFilters = React.useCallback(
    (newFilters: Partial<FreshReleasesFilters>) => {
      setFreshReleasesFiltersState((prevFilters: FreshReleasesFilters) => ({
        ...prevFilters,
        ...newFilters,
      }));
    },
    []
  );

  const clearSavedFilters = React.useCallback(() => {
    const storageKey = getStorageKey(pageType);
    filterStore.removeItem(storageKey);
    setFreshReleasesFiltersState(DEFAULT_FILTERS);
  }, [pageType]);

  return { freshReleasesFilters, setFreshReleasesFilters, clearSavedFilters };
}
