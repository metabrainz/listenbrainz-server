import * as React from "react";
import { getAlbumArtFromReleaseMBID } from "../utils/utils";
import { formatReleaseDate } from "./utils";

type ReleaseCardProps = {
  releaseDate: string;
  artistMBIDs: Array<string>;
  releaseMBID: string;
  releaseName: string;
  artistCreditName: string;
  releaseTypePrimary: string | undefined | null;
  releaseTypeSecondary: string | undefined | null;
  confidence?: number | null;
};

export default function ReleaseCard(props: ReleaseCardProps) {
  const {
    releaseMBID,
    releaseDate,
    releaseName,
    artistMBIDs,
    artistCreditName,
    releaseTypePrimary,
    releaseTypeSecondary,
    confidence,
  } = props;

  const COVERART_PLACEHOLDER = "/static/img/cover-art-placeholder.jpg";
  const RELEASE_TYPE_UNKNOWN = "Unknown";

  const [coverartSrc, setCoverartSrc] = React.useState<string>(
    COVERART_PLACEHOLDER
  );

  function releaseTypeTooltip(): string | undefined | null {
    if (
      (releaseTypeSecondary !== undefined &&
        releaseTypePrimary === undefined) ||
      (releaseTypeSecondary !== null && releaseTypePrimary === null)
    )
      return releaseTypeSecondary;

    if (
      (releaseTypePrimary !== undefined &&
        releaseTypeSecondary === undefined) ||
      (releaseTypePrimary !== null && releaseTypeSecondary === null)
    )
      return releaseTypePrimary;

    if (
      (releaseTypePrimary === undefined &&
        releaseTypeSecondary === undefined) ||
      (releaseTypePrimary === null && releaseTypeSecondary === null)
    )
      return "";

    return `${releaseTypePrimary} + ${releaseTypeSecondary}`;
  }

  async function getCoverArt() {
    const coverartURL = await getAlbumArtFromReleaseMBID(releaseMBID);
    if (coverartURL) {
      setCoverartSrc(coverartURL);
    }
  }

  React.useEffect(() => {
    getCoverArt();
  }, []);

  return (
    <div className="release-card-container">
      <div className="release-date">{formatReleaseDate(releaseDate)}</div>
      <img
        className="release-coverart"
        src={coverartSrc}
        alt={`${releaseName} by ${artistCreditName}`}
        loading="lazy"
      />
      <div className="name-type-container">
        <div className="release-name" title={releaseName}>
          <a
            href={`https://musicbrainz.org/release/${releaseMBID}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {releaseName}
          </a>
        </div>
        <div className="release-type-chip" title={releaseTypeTooltip()!}>
          {releaseTypeSecondary || releaseTypePrimary || RELEASE_TYPE_UNKNOWN}
        </div>
      </div>
      <div className="release-artist" title={artistCreditName}>
        <a
          href={`https://musicbrainz.org/artist/${artistMBIDs[0]}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {artistCreditName}
        </a>
      </div>
    </div>
  );
}
