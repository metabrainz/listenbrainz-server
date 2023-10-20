import * as React from "react";
import ReleaseCard from "./ReleaseCard";
import { formatReleaseDate } from "./utils";

type ReleaseCardReleaseProps = {
  filteredList: Array<FreshReleaseItem>;
  displaySettings: { [key: string]: boolean };
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
  return filteredList.reduce((acc, release) => {
    const { release_name: releaseName } = release;
    if (acc.has(releaseName.charAt(0).toUpperCase())) {
      acc.get(releaseName.charAt(0).toUpperCase()).push(release);
    } else {
      acc.set(releaseName.charAt(0).toUpperCase(), [release]);
    }
    return acc;
  }, new Map());
};

export default function ReleaseCardsGrid(props: ReleaseCardReleaseProps) {
  const { filteredList, displaySettings, order } = props;

  const releaseMapping = getMapping(order, filteredList);

  return (
    <div className="col-xs-12 col-md-11">
      {Array.from(releaseMapping?.entries()).map(([releaseDate, releases]) => (
        <>
          <div className="release-card-grid-title">
            {order === "release_date"
              ? formatReleaseDate(releaseDate)
              : releaseDate.charAt(0).toUpperCase()}
          </div>
          <div key={releaseDate} id="release-cards-grid">
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
                displaySettings={displaySettings}
                releaseTags={release.release_tags}
                listenCount={release.listen_count}
              />
            ))}
          </div>
        </>
      ))}
    </div>
  );
}
