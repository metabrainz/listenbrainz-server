import * as React from "react";
import { LazyLoadImage } from "react-lazy-load-image-component";
import { faPlay, faHourglass } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { isArray, isString, isUndefined } from "lodash";
import { Link } from "react-router-dom";
import { isValid } from "date-fns";
import { formatListenCount, formatReleaseDate } from "../utils";
import {
  generateAlbumArtThumbnailLink,
  getAlbumArtFromReleaseGroupMBID,
  getAlbumArtFromReleaseMBID,
} from "../../../utils/utils";
import Pill from "../../../components/Pill";

type ReleaseCardProps = {
  releaseDate?: string;
  artistMBIDs: Array<string>;
  releaseMBID?: string;
  releaseGroupMBID?: string;
  releaseName: string;
  artistCreditName: string;
  artistCredits?: Array<MBIDMappingArtist>;
  releaseTypePrimary?: string | null;
  releaseTypeSecondary?: string | null;
  confidence?: number | null;
  caaID: number | null;
  caaReleaseMBID: string | null;
  showReleaseTitle?: boolean;
  showArtist?: boolean;
  showInformation?: boolean;
  showTags?: boolean;
  showListens?: boolean;
  releaseTags?: Array<string>;
  listenCount?: number;
  dateFormatOptions?: Intl.DateTimeFormatOptions;
  onClick?:
    | React.MouseEventHandler<HTMLElement>
    | React.KeyboardEventHandler<HTMLElement>;
};

export default function ReleaseCard(props: ReleaseCardProps) {
  const {
    releaseMBID,
    releaseGroupMBID,
    releaseDate,
    dateFormatOptions,
    releaseName,
    artistMBIDs,
    artistCreditName,
    artistCredits,
    releaseTypePrimary,
    releaseTypeSecondary,
    confidence,
    caaID,
    caaReleaseMBID,
    onClick,
    showReleaseTitle,
    showArtist,
    showInformation,
    showTags,
    showListens,
    releaseTags,
    listenCount,
  } = props;

  const [imageLoaded, setImageLoaded] = React.useState(false);

  const hasReleaseDate =
    !isUndefined(releaseDate) &&
    isString(releaseDate) &&
    Boolean(releaseDate.length) &&
    isValid(new Date(releaseDate));
  const futureRelease = hasReleaseDate && new Date(releaseDate) > new Date();
  const COVERART_PLACEHOLDER = "/static/img/cover-art-placeholder.jpg";
  const RELEASE_TYPE_UNKNOWN = "Unknown";

  const [coverartSrc, setCoverartSrc] = React.useState<string>();

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

  const releaseCoverArtIcon = (
    <FontAwesomeIcon icon={futureRelease ? faHourglass : faPlay} />
  );
  const coverArtPlaceholder = (
    <div
      className={`release-coverart-placeholder release-coverart ${
        imageLoaded ? "hide-placeholder" : ""
      }`}
    >
      {releaseCoverArtIcon}
    </div>
  );

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  React.useEffect(() => {
    async function getCoverArt() {
      let coverartURL;
      if (releaseMBID || releaseGroupMBID) {
        coverartURL = await getAlbumArtFromReleaseMBID(
          releaseMBID,
          releaseGroupMBID
        );
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

  let linkToEntity: string;
  if (releaseGroupMBID) {
    linkToEntity = `/album/${releaseGroupMBID}/`;
  } else if (releaseMBID) {
    linkToEntity = `/release/${releaseMBID}/`;
  } else {
    linkToEntity = `/search/?search_type=album&search_term=${releaseName}+${artistCreditName}`;
  }

  const coverArtElement = coverartSrc ? (
    <>
      {coverArtPlaceholder}
      <LazyLoadImage
        className={`release-coverart ${imageLoaded ? "" : "hide-image"}`}
        src={coverartSrc}
        alt={`${releaseName} by ${artistCreditName}`}
        onLoad={handleImageLoad}
      />
      <div className="hover-backdrop">{releaseCoverArtIcon}</div>
    </>
  ) : (
    <div className="release-coverart release-coverart-placeholder">
      {releaseCoverArtIcon}
    </div>
  );
  return (
    <div className="release-card-container" key={releaseMBID}>
      <div className="release-item">
        {showListens && listenCount ? (
          <div className="listen-count">
            <Pill title="Listens" type="secondary" active>
              <>
                <FontAwesomeIcon icon={faPlay} />
                <span className="listen-count-number">
                  {formatListenCount(listenCount)}
                </span>
              </>
            </Pill>
          </div>
        ) : null}
        <div className="release-information">
          {showTags && releaseTags && releaseTags.length ? (
            <div className="cover-art-info">
              {releaseTags.join(", ").length > 26 ? (
                <div className="tags" title={releaseTags.join(", ")}>
                  {releaseTags.join(", ").substring(0, 23)}...
                </div>
              ) : (
                <div className="tags">{releaseTags.join(", ")}</div>
              )}
            </div>
          ) : null}
          {showInformation && (
            <div className="cover-art-info">
              <div className="release-type-chip" title={releaseTypeTooltip()!}>
                {releaseTypeSecondary ||
                  releaseTypePrimary ||
                  RELEASE_TYPE_UNKNOWN}
              </div>
              {hasReleaseDate && (
                <div
                  className="release-date"
                  title={formatReleaseDate(releaseDate, {
                    year: "numeric",
                    month: "long",
                    day: "2-digit",
                  })}
                >
                  {formatReleaseDate(releaseDate, dateFormatOptions)}
                </div>
              )}
            </div>
          )}
        </div>
        {onClick ? (
          <div
            className="release-coverart-container"
            onClick={onClick as React.MouseEventHandler}
            onKeyDown={onClick as React.KeyboardEventHandler}
            role="button"
            tabIndex={0}
          >
            {coverArtElement}
          </div>
        ) : (
          <Link to={linkToEntity} className="release-coverart-container">
            {coverArtElement}
          </Link>
        )}
      </div>
      {showReleaseTitle && (
        <div className="name-type-container">
          <div className="release-name" title={releaseName}>
            <Link to={linkToEntity}>{releaseName}</Link>
          </div>
        </div>
      )}
      {showArtist && isArray(artistCredits) && artistCredits.length && (
        <div className="release-artist" title={artistCreditName}>
          {artistCredits.map((ac) => (
            <span key={ac.artist_mbid}>
              <Link to={`/artist/${ac.artist_mbid}/`}>
                {ac.artist_credit_name}
              </Link>
              {ac.join_phrase}
            </span>
          ))}
        </div>
      )}
      {showArtist && !isArray(artistCredits) && (
        <div className="release-artist" title={artistCreditName}>
          <Link
            to={
              artistMBIDs.length
                ? `/artist/${artistMBIDs[0]}/`
                : `/search/?search_type=artist&search_term=${artistCreditName}`
            }
          >
            {artistCreditName}
          </Link>
        </div>
      )}
    </div>
  );
}
