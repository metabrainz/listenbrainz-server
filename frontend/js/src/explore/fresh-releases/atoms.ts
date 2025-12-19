import { atomWithStorage } from "jotai/utils";
import {
  DisplaySettingsPropertiesEnum,
  filterRangeOption,
  SortOption,
  SortDirection,
  PAGE_TYPE_SITEWIDE,
} from "./constants";

export const pageTypeAtom = atomWithStorage<string>(
  "lb_fresh_page_type",
  PAGE_TYPE_SITEWIDE
);

export const rangeAtom = atomWithStorage<filterRangeOption>(
  "lb_fresh_range",
  "week"
);

export const displaySettingsAtom = atomWithStorage(
  "lb_fresh_display_settings",
  {
    [DisplaySettingsPropertiesEnum.releaseTitle]: true,
    [DisplaySettingsPropertiesEnum.artist]: true,
    [DisplaySettingsPropertiesEnum.information]: true,
    [DisplaySettingsPropertiesEnum.tags]: false,
    [DisplaySettingsPropertiesEnum.listens]: false,
  }
);

export const showPastReleasesAtom = atomWithStorage<boolean>(
  "lb_fresh_show_past",
  true
);

export const showFutureReleasesAtom = atomWithStorage<boolean>(
  "lb_fresh_show_future",
  true
);

export const sortAtom = atomWithStorage<SortOption>(
  "lb_fresh_sort",
  "release_date"
);

export const sortDirectionAtom = atomWithStorage<SortDirection>(
  "lb_fresh_sort_dir",
  "descend"
);
