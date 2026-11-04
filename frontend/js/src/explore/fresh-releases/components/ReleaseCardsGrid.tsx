import * as React from "react";
import ReleaseCard from "./ReleaseCard";
import { formatReleaseDate, getKeyForOrder } from "../utils";
import type { DisplaySettings, SortDirection } from "../FreshReleases";

type ReleaseCardReleaseProps = {
  filteredList: Array<FreshReleaseItem>;
  displaySettings: DisplaySettings;
  order: string;
  direction: SortDirection;
};

const getMapping = (
  releaseOrder: string,
  filteredList: Array<FreshReleaseItem>
): Map<string, Array<FreshReleaseItem>> => {
  return filteredList.reduce((acc, release) => {
    const key = getKeyForOrder(releaseOrder, release);
    if (acc.has(key)) {
      acc.get(key)!.push(release);
    } else {
      acc.set(key, [release]);
    }
    return acc;
  }, new Map<string, Array<FreshReleaseItem>>());
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
    if (release_order === "release_date") {
      // releaseKey is an ISO date string like "2025-01-17"
      return formatReleaseDate(releaseKey);
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
          {/* Keep the scroll target in normal flow when the title becomes sticky. */}
          <div
            className="release-card-grid-anchor"
            data-group-key={releaseKey}
            aria-hidden="true"
          />
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
