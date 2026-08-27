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

  const setFreshReleasesFilters = React.useCallback(
    (newFilters: Partial<FreshReleasesFilters>) => {
      setFreshReleasesFiltersState((prevFilters: FreshReleasesFilters) => {
        const updatedFilters = { ...prevFilters, ...newFilters };
        const storageKey = getStorageKey(pageType);
        filterStore.setItem(storageKey, updatedFilters);
        return updatedFilters;
      });
    },
    [pageType]
  );

  const clearSavedFilters = React.useCallback(() => {
    const storageKey = getStorageKey(pageType);
    filterStore.removeItem(storageKey);
    setFreshReleasesFiltersState(DEFAULT_FILTERS);
  }, [pageType]);

  return { freshReleasesFilters, setFreshReleasesFilters, clearSavedFilters };
}
