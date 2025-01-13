/* eslint-disable jsx-a11y/anchor-is-valid */

import * as React from "react";
import { useContext } from "react";

import { Link } from "react-router-dom";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../utils/GlobalAppContext";
import { COLOR_LB_ORANGE } from "../utils/constants";

type ExploreCardProps = {
  name: string;
  desc: string;
  img_name: string;
  url: string;
};

function ExploreCard(props: ExploreCardProps) {
  const { name, desc, img_name, url } = props;
  return (
    <div className="explore-card-container">
      <div className="explore-card">
        <Link to={url}>
          <div className="explore-card-img-overlay"> </div>
        </Link>
        <div className="explore-card-img-clip flex-center">
          <img
            src={`/static/img/explore/${img_name}`}
            alt={name}
            className="explore-card-img"
          />
        </div>
        <div className="explore-card-text">
          <div className="explore-card-text-name">
            <Link to={url}>{name}</Link>
          </div>
          <div>{desc}</div>
        </div>
      </div>
    </div>
  );
}

export default function ExplorePage() {
  const { currentUser } = useContext(GlobalAppContext);
  return (
    <div role="main">
      <Helmet>
        <title>Explore</title>
      </Helmet>
      <div className="row">
        <div>
          <ExploreCard
            name="Fresh Releases"
            desc="Discover"
            img_name="fresh-releases.jpg"
            url="/explore/fresh-releases/"
          />
        </div>
        <div>
          <ExploreCard
            name="Link listens"
            desc="Fix your unlinked listens"
            img_name="link-listens.jpg"
            url="/settings/link-listens/"
          />
        </div>
        <div>
          <ExploreCard
            name="Hue Sound"
            desc="Discover"
            img_name="huesound.jpg"
            url="/explore/huesound/"
          />
        </div>
        <div>
          <ExploreCard
            name="Cover Art Collage"
            desc="Discover"
            img_name="cover-art-collage.jpg"
            url="/explore/cover-art-collage/"
          />
        </div>
        <div>
          <ExploreCard
            name="Music Neighborhood"
            desc="Visualisation"
            img_name="music-neighborhood.jpg"
            url="/explore/music-neighborhood/"
          />
        </div>
        <div>
          <ExploreCard
            name="Top Similar Users"
            desc="Social"
            img_name="similar-users.jpg"
            url="/explore/similar-users/"
          />
        </div>
      </div>
      {currentUser?.name && (
        <>
          <div className="explore-page-divider">
            <h3>Your year in music</h3>
            <hr />
          </div>
          <div className="row">
            <div>
              <ExploreCard
                name="Your Year in Music 2024"
                desc="Review"
                img_name="year-in-music-2024.png"
                url={`/user/${currentUser.name}/year-in-music/2024/`}
              />
            </div>
            <div>
              <ExploreCard
                name="Your Year in Music 2023"
                desc="Review"
                img_name="year-in-music-2023.jpg"
                url={`/user/${currentUser.name}/year-in-music/2023/`}
              />
            </div>
            <div>
              <ExploreCard
                name="Your Year in Music 2022"
                desc="Review"
                img_name="year-in-music-2022.jpg"
                url={`/user/${currentUser.name}/year-in-music/2022/`}
              />
            </div>
            <div>
              <ExploreCard
                name="Your Year in Music 2021"
                desc="Review"
                img_name="year-in-music-2021.jpg"
                url={`/user/${currentUser.name}/year-in-music/2021/`}
              />
            </div>
          </div>
        </>
      )}
      <div className="explore-page-divider">
        <h3>Beta</h3>
        <hr />
      </div>
      <div className="row">
        <ExploreCard
          name="ListenBrainz Radio"
          desc="Instant custom playlists"
          img_name="lb-radio-beta.jpg"
          url="/explore/lb-radio/"
        />
        <ExploreCard
          name="Stats art generator"
          desc="Visualize and share your stats"
          img_name="stats-art-beta.jpg"
          url="/explore/art-creator/"
        />
      </div>
    </div>
  );
}
