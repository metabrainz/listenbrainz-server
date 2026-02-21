/* eslint-disable jsx-a11y/anchor-is-valid */

import * as React from "react";
import { useContext } from "react";

import { Link } from "react-router";
import { Helmet } from "react-helmet";
import { Accordion } from "react-bootstrap";
import GlobalAppContext from "../utils/GlobalAppContext";

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
        <ExploreCard
          name="Art Creator"
          desc="Share your album grids and other stats art"
          img_name="art-creator.jpg"
          url="/explore/art-creator/"
        />
        <ExploreCard
          name="Fresh Releases"
          desc="Discover"
          img_name="fresh-releases.jpg"
          url="/explore/fresh-releases/"
        />
        <ExploreCard
          name="Year in Music"
          desc="Yearly breakdown of your listening habits"
          img_name="year-in-music.png"
          url="/my/year-in-music/"
        />
        <ExploreCard
          name="Link listens"
          desc="Fix your unlinked listens"
          img_name="link-listens.jpg"
          url="/settings/link-listens/"
        />
        <ExploreCard
          name="Hue Sound"
          desc="Discover"
          img_name="huesound.jpg"
          url="/explore/huesound/"
        />
        <ExploreCard
          name="Music Neighborhood"
          desc="Visualisation"
          img_name="music-neighborhood.jpg"
          url="/explore/music-neighborhood/"
        />
        <ExploreCard
          name="Top Similar Users"
          desc="Social"
          img_name="similar-users.jpg"
          url="/explore/similar-users/"
        />
        <ExploreCard
          name="Genre Explorer"
          desc="Discover music by genre"
          img_name="cover-art-collage.jpg"
          url="/explore/genre/rock/"
        />
      </div>

      <Accordion
        alwaysOpen
        defaultActiveKey={["beta"]}
        className="explore-sections"
      >
        {/* Beta Section */}
        <Accordion.Item eventKey="beta">
          <Accordion.Header as="div" className="explore-page-divider">
            <h3>Beta</h3>
            <hr />
          </Accordion.Header>
          <Accordion.Body>
            <div className="row">
              <ExploreCard
                name="ListenBrainz Radio"
                desc="Instant custom playlists"
                img_name="lb-radio-beta.jpg"
                url="/explore/lb-radio/"
              />

              <ExploreCard
                name="Widgets"
                desc="Embed ListenBrainz elements into your website"
                img_name="lb-widgets-beta.jpg"
                url="https://listenbrainz.readthedocs.io/en/latest/users/widgets.html"
              />
            </div>
          </Accordion.Body>
        </Accordion.Item>

        {/* Archived Section */}
        {currentUser?.name && (
          <Accordion.Item eventKey="archived">
            <Accordion.Header as="div" className="explore-page-divider">
              <h3>Archived</h3>
              <hr />
            </Accordion.Header>
            <Accordion.Body>
              <div className="row">
                <ExploreCard
                  name="Cover Art Collage"
                  desc="Discover"
                  img_name="cover-art-collage.jpg"
                  url="/explore/cover-art-collage/"
                />

                <ExploreCard
                  name="Your Year in Music 2024"
                  desc="Archival version of Year In Music 2024"
                  img_name="year-in-music-2024.png"
                  url={`/user/${encodeURIComponent(
                    currentUser.name
                  )}/year-in-music/legacy/2024/`}
                />

                <ExploreCard
                  name="Your Year in Music 2023"
                  desc="Archival version of Year In Music 2023"
                  img_name="year-in-music-2023.jpg"
                  url={`/user/${encodeURIComponent(
                    currentUser.name
                  )}/year-in-music/legacy/2023/`}
                />

                <ExploreCard
                  name="Your Year in Music 2022"
                  desc="Archival version of Year In Music 2022"
                  img_name="year-in-music-2022.jpg"
                  url={`/user/${encodeURIComponent(
                    currentUser.name
                  )}/year-in-music/legacy/2022/`}
                />
                <ExploreCard
                  name="Your Year in Music 2021"
                  desc="Archival version of Year In Music 2021"
                  img_name="year-in-music-2021.jpg"
                  url={`/user/${encodeURIComponent(
                    currentUser.name
                  )}/year-in-music/legacy/2021/`}
                />
              </div>
            </Accordion.Body>
          </Accordion.Item>
        )}
      </Accordion>
    </div>
  );
}
