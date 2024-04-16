import * as React from "react";
import { includes as _includes } from "lodash";

import { faCircleInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link } from "react-router-dom";
import ReactTooltip from "react-tooltip";
import Card from "../../../components/Card";
import SimilarityScore from "./SimilarityScore";
import GlobalAppContext from "../../../utils/GlobalAppContext";

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
  const { currentUser } = React.useContext(GlobalAppContext);

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
      <div className="info-icon" data-tip data-for="info-tooltip">
        <Link
          to={`/user/${currentUser?.name}/stats/?range=all_time`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <FontAwesomeIcon icon={faCircleInfo} />
        </Link>
      </div>
      <span>Your compatibility with {user.name} :</span>
      <SimilarityScore
        similarityScore={similarityScore}
        user={user}
        type="compact"
      />
      <hr />
      {content}
      <ReactTooltip id="info-tooltip" place="top">
        These artists are calculated on the basis of the top 100 <br />
        artists of all time for both of the users. Click for more stats!
      </ReactTooltip>
    </Card>
  );
}

export default CompatibilityCard;
