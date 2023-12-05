import * as React from "react";
import { LazyLoadImage } from "react-lazy-load-image-component";
import { formatReleaseDate } from "./utils";
import {
  generateAlbumArtThumbnailLink,
  getAlbumArtFromReleaseGroupMBID,
  getAlbumArtFromReleaseMBID,
} from "../../utils/utils";
import type { ReleaseGroupArtist } from "../../entity-pages/utils";

type ReleaseCardProps = {
  releaseDate: string;
  artistMBIDs: Array<string>;
  releaseMBID?: string;
  releaseGroupMBID?: string;
  releaseName: string;
  artistCreditName: string;
  releaseTypePrimary?: string | null;
  releaseTypeSecondary?: string | null;
  confidence?: number | null;
  caaID: number | null;
  caaReleaseMBID: string | null;
  artistCredits?: ReleaseGroupArtist[];
};

export default function ReleaseCard(props: ReleaseCardProps) {
  const {
    releaseMBID,
    releaseGroupMBID,
    releaseDate,
    releaseName,
    artistMBIDs,
    artistCreditName,
    releaseTypePrimary,
    releaseTypeSecondary,
    confidence,
    caaID,
    caaReleaseMBID,
    artistCredits,
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

  React.useEffect(() => {
    async function getCoverArt() {
      let coverartURL;
      if (releaseMBID) {
        coverartURL = await getAlbumArtFromReleaseMBID(
          releaseMBID,
          releaseGroupMBID ?? true
        );
      } else if (releaseGroupMBID) {
        coverartURL = await getAlbumArtFromReleaseGroupMBID(releaseGroupMBID);
      }
      if (coverartURL) {
        setCoverartSrc(coverartURL);
      }
    }

    if (caaID && caaReleaseMBID) {
      const coverartURL = generateAlbumArtThumbnailLink(caaID, caaReleaseMBID);
      setCoverartSrc(coverartURL);
    } else {
      getCoverArt();
    }
  }, [releaseMBID, releaseGroupMBID, caaID, caaReleaseMBID, setCoverartSrc]);
  const linkToEntity = releaseGroupMBID
    ? `/album/${releaseGroupMBID}`
    : `/player/release/${releaseMBID}`;
  return (
    <div className="release-card-container">
      <div className="release-date">{formatReleaseDate(releaseDate)}</div>
      <a href={linkToEntity} target="_blank" rel="noopener noreferrer">
        <LazyLoadImage
          className="release-coverart"
          src={coverartSrc}
          alt={`${releaseName} by ${artistCreditName}`}
          placeholderSrc={COVERART_PLACEHOLDER}
        />
      </a>
      <div className="name-type-container">
        <div className="release-name" title={releaseName}>
          <a href={linkToEntity} target="_blank" rel="noopener noreferrer">
            {releaseName}
          </a>
        </div>
        <div className="release-type-chip" title={releaseTypeTooltip()!}>
          {releaseTypeSecondary || releaseTypePrimary || RELEASE_TYPE_UNKNOWN}
        </div>
      </div>
      {artistCredits && artistCredits.length ? (
        <div
          className="release-artist"
          title={artistCredits
            .map((ac) => ac.artist_credit_name + ac.join_phrase)
            .join("")}
        >
          {artistCredits.map((ac) => (
            <>
              <a
                href={`/artist/${ac.artist_mbid}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {ac.artist_credit_name}
              </a>
              {ac.join_phrase}
            </>
          ))}
        </div>
      ) : (
        <div className="release-artist" title={artistCreditName}>
          <a
            href={`/artist/${artistMBIDs[0]}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {artistCreditName}
          </a>
        </div>
      )}
    </div>
  );
}
