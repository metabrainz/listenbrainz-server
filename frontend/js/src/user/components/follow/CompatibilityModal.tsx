import * as React from "react";
import { includes as _includes } from "lodash";

import Card from "../../../components/Card";
import SimilarityScore from "./SimilarityScore";

export type CompatibilityModalProps = {
  user: ListenBrainzUser;
  similarityScore: number;
  similarArtists: Array<{
    artist_name: string;
    artist_mbid: string | null;
    listen_count: number;
  }>;
};

function CompatibilityModal(props: CompatibilityModalProps) {
  const { user, similarityScore, similarArtists } = props;

  let content;

  if (similarArtists.length > 0) {
    content = (
      <div className="similarity-empty text-center">
        {"You both listen to "}
        {similarArtists.map((artist, index) => {
          return (
            <span>
              {index > 0 && ", "}
              {index > 0 && index === similarArtists.length - 1 ? "and " : ""}
              {artist.artist_mbid !== null ? (
                <a
                  href={`/artist/${artist.artist_mbid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={artist.artist_name}
                >
                  {artist.artist_name}
                </a>
              ) : (
                `${artist.artist_name}`
              )}
            </span>
          );
        })}
      </div>
    );
  } else {
    content = (
      <div className="similarity-empty text-center">
        You have no common artists.
      </div>
    );
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

export default CompatibilityModal;
