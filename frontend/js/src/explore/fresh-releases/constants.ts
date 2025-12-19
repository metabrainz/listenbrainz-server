export enum DisplaySettingsPropertiesEnum {
  releaseTitle = "Release Title",
  artist = "Artist",
  information = "Information",
  tags = "Tags",
  listens = "Listens",
}

export type DisplaySettings = {
  [key in DisplaySettingsPropertiesEnum]: boolean;
};

export const SortOptions = {
  releaseDate: {
    value: "release_date",
    label: "Release Date",
  },
  artist: {
    value: "artist_credit_name",
    label: "Artist",
  },
  releaseTitle: {
    value: "release_name",
    label: "Release Title",
  },
  confidence: {
    value: "confidence",
    label: "Confidence",
  },
} as const;

export type SortOption = typeof SortOptions[keyof typeof SortOptions]["value"];

export const SortDirections = {
  ascend: {
    value: "ascend",
    label: "Ascending",
  },
  descend: {
    value: "descend",
    label: "Descending",
  },
};

export type SortDirection = typeof SortDirections[keyof typeof SortDirections]["value"];

export const DefaultSortDirections: Record<SortOption, SortDirection> = {
  release_date: "descend",
  artist_credit_name: "ascend",
  release_name: "ascend",
  confidence: "descend",
};

export const filterRangeOptions = {
  week: {
    value: 7,
    key: "week",
    label: "Week",
  },
  month: {
    value: 30,
    key: "month",
    label: "Month",
  },
  three_months: {
    value: 90,
    key: "three_months",
    label: "3 Months",
  },
} as const;

export type filterRangeOption = keyof typeof filterRangeOptions;

export const PAGE_TYPE_USER: string = "user";
export const PAGE_TYPE_SITEWIDE: string = "sitewide";
