import React, { useState, useEffect } from "react";
import { formattedReleaseDate, getCoverartFromReleaseMBID } from "./utils";

type ReleaseCardProps = {
  releaseDate: string;
  artistMBIDs: Array<string>;
  releaseMBID: string;
  releaseName: string;
  artistCreditName: string;
  releaseType: string;
};

export default function ReleaseCard(props: ReleaseCardProps) {
  const {
    releaseMBID,
    releaseDate,
    releaseName,
    releaseType,
    artistMBIDs,
    artistCreditName,
  } = props;

  const COVERART_PLACEHOLDER = "/static/img/cover-art-placeholder.jpg";

  const [coverartSrc, setCoverartSrc] = useState<string>(COVERART_PLACEHOLDER);

  const getCoverArt = async () => {
    const coverartURL = await getCoverartFromReleaseMBID(releaseMBID);
    if (coverartURL) {
      setCoverartSrc(coverartURL);
    }
  };

  useEffect(() => {
    getCoverArt();
  }, []);

  return (
    <div className="release-card-container">
      <div className="release-date">{formattedReleaseDate(releaseDate)}</div>
      <img
        className="release-coverart"
        src={coverartSrc}
        alt={`${releaseName} by ${artistCreditName}`}
        loading="lazy"
      />
      <div className="name-type-container">
        <div className="release-name">
          <a
            href={`https://musicbrainz.org/release/${releaseMBID}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {releaseName}
          </a>
        </div>
        <div className="release-type-chip">{releaseType}</div>
      </div>
      <div className="release-artist">
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
