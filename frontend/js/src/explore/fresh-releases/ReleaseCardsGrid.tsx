import * as React from "react";
import ReleaseCard from "./ReleaseCard";
import { formatReleaseDate } from "./utils";
import type { DisplaySettings } from "./FreshReleases";

type ReleaseCardReleaseProps = {
  filteredList: Array<FreshReleaseItem>;
  displaySettings: DisplaySettings;
  order: string;
};

const getMapping = (
  releaseOrder: string,
  filteredList: Array<FreshReleaseItem>
): Map<string, Array<FreshReleaseItem>> => {
  if (releaseOrder === "release_date") {
    return filteredList.reduce((acc, release) => {
      const { release_date: releaseDate } = release;
      if (acc.has(releaseDate)) {
        acc.get(releaseDate).push(release);
      } else {
        acc.set(releaseDate, [release]);
      }
      return acc;
    }, new Map());
  }
  if (releaseOrder === "artist_credit_name") {
    return filteredList.reduce((acc, release) => {
      const { artist_credit_name: artistCreditName } = release;
      if (acc.has(artistCreditName.charAt(0).toUpperCase())) {
        acc.get(artistCreditName.charAt(0).toUpperCase()).push(release);
      } else {
        acc.set(artistCreditName.charAt(0).toUpperCase(), [release]);
      }
      return acc;
    }, new Map());
  }
  if (releaseOrder === "release_name") {
    return filteredList.reduce((acc, release) => {
      const { release_name: releaseName } = release;
      if (acc.has(releaseName.charAt(0).toUpperCase())) {
        acc.get(releaseName.charAt(0).toUpperCase()).push(release);
      } else {
        acc.set(releaseName.charAt(0).toUpperCase(), [release]);
      }
      return acc;
    }, new Map());
  }
  return filteredList.reduce((acc, release) => {
    const { confidence } = release;
    if (acc.has(confidence)) {
      acc.get(confidence).push(release);
    } else {
      acc.set(confidence, [release]);
    }
    return acc;
  }, new Map());
};

export default function ReleaseCardsGrid(props: ReleaseCardReleaseProps) {
  const { filteredList, displaySettings, order } = props;

  const releaseMapping = getMapping(order, filteredList);

  const getReleaseCardGridTitle = (
    releaseKey: string,
    release_order: string
  ): string => {
    if (release_order === "release_date") {
      return formatReleaseDate(releaseKey);
    }
    if (
      release_order === "artist_credit_name" ||
      release_order === "release_name"
    ) {
      return releaseKey.charAt(0).toUpperCase();
    }
    return releaseKey;
  };

  return (
    <>
      {Array.from(releaseMapping?.entries()).map(([releaseKey, releases]) => (
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
