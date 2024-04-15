import * as React from "react";
import { includes as _includes } from "lodash";

import { Link } from "react-router-dom";
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
  const { user, similarityScore, similarArtists } = props;

  let content;

  if (similarArtists.length > 0) {
    content = (
      <div className="text-center">
        {"You both listen to "}
        {similarArtists.map((artist, index) => {
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
      </div>
    );
  } else {
    content = <div className="text-center">You have no common artists.</div>;
  }

  return (
    <Card id="compatibility-card" data-testid="compatibility-card">
      <span>Your compatibility with {user.name} :</span>
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
