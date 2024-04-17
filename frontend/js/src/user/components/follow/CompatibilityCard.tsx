import * as React from "react";
import { includes as _includes } from "lodash";

import { faCircleInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router-dom";
import ReactTooltip from "react-tooltip";
import Card from "../../../components/Card";
import SimilarityScore from "./SimilarityScore";

export type CompatibilityCardProps = {
  user: ListenBrainzUser;
  similarityScore: number;
  similarArtists: Array<{
    artist_name: string;
    artist_mbid: string | null;
    listen_count: number;
  }>;
};

function CompatibilityCard(props: CompatibilityCardProps) {
  const { user, similarityScore } = props;
  let { similarArtists } = props;

  let content;
  let isSliced = false;

  if (similarArtists.length > 25) {
    similarArtists = similarArtists.slice(0, 26);
    isSliced = true;
  }

  if (similarArtists.length > 0) {
    content = (
      <div className="text-center">
        {"You both listen to "}
        {similarArtists
          .slice(...(similarArtists.length > 5 ? [0, 5] : [0]))
          .map((artist, index) => {
            return (
              <span>
                {index > 0 && ", "}
                {index > 0 && index === similarArtists.length - 1 ? "and " : ""}
                {artist.artist_mbid !== null ? (
                  <Link
                    to={`/artist/${artist.artist_mbid}`}
                    title={artist.artist_name}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {artist.artist_name}
                  </Link>
                ) : (
                  `${artist.artist_name}`
                )}
              </span>
            );
          })}
        {similarArtists.length > 5 && (
          <>
            <span data-tip data-for="more-artists-tooltip">
              , and more.
            </span>
            <ReactTooltip id="more-artists-tooltip" place="top">
              {similarArtists.slice(5, -1).map((artist, index) => {
                return (
                  <span>
                    {index > 0 && ", "}
                    {index > 0 && index === similarArtists.length - 1
                      ? "and "
                      : ""}
                    {index > 0 && index % 5 === 0 && <br />}
                    {`${artist.artist_name}`}
                  </span>
                );
              })}
              {isSliced && <span> and even more.</span>}
            </ReactTooltip>
          </>
        )}
      </div>
    );
  } else {
    content = <div className="text-center">You have no common artists.</div>;
  }

  return (
    <Card id="compatibility-card" data-testid="compatibility-card">
      <div className="info-icon" data-tip data-for="info-tooltip">
        <Link
          to={`/user/${user?.name}/stats/?range=all_time`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <FontAwesomeIcon icon={faCircleInfo} />
        </Link>
      </div>
      <span>Your compatibility with {user.name}:</span>
      <SimilarityScore
        similarityScore={similarityScore}
        user={user}
        type="compact"
      />
      <hr />
      {content}
      <ReactTooltip id="info-tooltip" place="top">
        Artists displayed are the top matches, comparing the top 100 most
        listened artists of all
        <br /> time for both users. Click here for more of their statistics.
      </ReactTooltip>
    </Card>
  );
}

export default CompatibilityCard;
