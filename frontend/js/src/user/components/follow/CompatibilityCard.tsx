import * as React from "react";
import { includes as _includes } from "lodash";

import { faCircleInfo, faSquarePlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router";
import Card from "../../../components/Card";
import Tooltip from "../../../components/Tooltip";
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
  const { user, similarityScore, similarArtists } = props;

  const firstFiveArtists = similarArtists.slice(0, 5);
  const otherArtists = similarArtists.slice(5, 25);
  const hasMoreThanFive = Boolean(otherArtists.length);
  const hasEvenMoreArtists = similarArtists.length > 25;

  let content;

  if (similarArtists.length > 0) {
    content = (
      <div className="text-center">
        {"You both listen to "}
        {firstFiveArtists.map((artist, index) => {
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
        {hasMoreThanFive && (
          <Tooltip
            id="more-artists-tooltip"
            placement="top"
            tooltip={
              <>
                {otherArtists.map((artist, index) => {
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
                {hasEvenMoreArtists && <span> and even more.</span>}
              </>
            }
          >
            <span>
              , and more.{" "}
              <FontAwesomeIcon icon={faSquarePlus} size="sm" color="gray" />
            </span>
          </Tooltip>
        )}
      </div>
    );
  } else {
    content = <div className="text-center">You have no common artists.</div>;
  }

  return (
    <Card id="compatibility-card" data-testid="compatibility-card">
      <Tooltip
        id="info-tooltip"
        placement="top"
        tooltip={
          <>
            Artists displayed are the top matches, comparing the top 100 most
            listened artists of all
            <br /> time for both users. Click here for their statistics.
          </>
        }
      >
        <div className="info-icon">
          <Link
            to={`/user/${encodeURIComponent(user.name)}/stats/?range=all_time`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <FontAwesomeIcon icon={faCircleInfo} />
          </Link>
        </div>
      </Tooltip>
      <span>Your compatibility with {user.name}:</span>
      <SimilarityScore
        similarityScore={similarityScore}
        user={user}
        type="compact"
      />
      <hr />
      {content}
    </Card>
  );
}

export default CompatibilityCard;
