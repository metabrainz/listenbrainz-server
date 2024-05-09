import * as React from "react";
import ReleaseCard from "./ReleaseCard";
import { formatReleaseDate } from "../utils";
import type { DisplaySettings, SortDirection } from "../FreshReleases";

type ReleaseCardReleaseProps = {
  filteredList: Array<FreshReleaseItem>;
  displaySettings: DisplaySettings;
  order: string;
  direction: SortDirection;
};

const getKeyForOrder = (
  releaseOrder: string,
  release: FreshReleaseItem
): string | number => {
  switch (releaseOrder) {
    case "release_date":
      return formatReleaseDate(release.release_date);
    case "artist_credit_name":
    case "release_name":
      return release[releaseOrder].charAt(0).toUpperCase();
    case "confidence":
      return release[releaseOrder]!;
    default:
      return "";
  }
};

const getMapping = (
  releaseOrder: string,
  filteredList: Array<FreshReleaseItem>
): Map<string, Array<FreshReleaseItem>> => {
  return filteredList.reduce((acc, release) => {
    const key = getKeyForOrder(releaseOrder, release);
    if (acc.has(key)) {
      acc.get(key).push(release);
    } else {
      acc.set(key, [release]);
    }
    return acc;
  }, new Map());
};

export default function ReleaseCardsGrid(props: ReleaseCardReleaseProps) {
  const { filteredList, displaySettings, order, direction } = props;

  const releaseMapping = React.useMemo(() => getMapping(order, filteredList), [
    order,
    filteredList,
  ]);

  const getReleaseCardGridTitle = (
    releaseKey: string,
    release_order: string
  ): string => {
    if (
      release_order === "artist_credit_name" ||
      release_order === "release_name"
    ) {
      return releaseKey.charAt(0).toUpperCase();
    }
    return releaseKey;
  };

  const mappedEntries = Array.from(releaseMapping?.entries());
  if (
    (order !== "confidence" && direction === "descend") ||
    (order === "confidence" && direction === "ascend")
  ) {
    mappedEntries.reverse();
  }

  return (
    <>
      {mappedEntries.map(([releaseKey, releases]) => (
        <React.Fragment key={`${releaseKey}-container`}>
          <div className="release-card-grid-title" key={`${releaseKey}-title`}>
            {getReleaseCardGridTitle(releaseKey, order)}
          </div>
          <div key={releaseKey} className="release-cards-grid">
            {releases?.map((release) => (
              <ReleaseCard
                key={release.release_mbid}
                releaseDate={release.release_date}
                releaseMBID={release.release_mbid}
                releaseName={release.release_name}
                releaseTypePrimary={release.release_group_primary_type}
                releaseTypeSecondary={release.release_group_secondary_type}
                artistCreditName={release.artist_credit_name}
                artistMBIDs={release.artist_mbids}
                confidence={release.confidence}
                caaID={release.caa_id}
                caaReleaseMBID={release.caa_release_mbid}
                showReleaseTitle={displaySettings["Release Title"]}
                showArtist={displaySettings.Artist}
                showInformation={displaySettings.Information}
                showTags={displaySettings.Tags}
                showListens={displaySettings.Listens}
                releaseTags={release.release_tags}
                listenCount={release.listen_count}
              />
            ))}
          </div>
        </React.Fragment>
      ))}
    </>
  );
}
