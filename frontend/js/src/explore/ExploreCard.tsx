/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import { useContext } from "react";
import { getPageProps } from "../utils/utils";

import ErrorBoundary from "../utils/ErrorBoundary";
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
        <a href={url}>
          <div className="explore-card-img-overlay"> </div>
        </a>
        <div className="explore-card-img-clip flex-center">
          <img
            src={`/static/img/explore/${img_name}`}
            alt={name}
            className="explore-card-img"
          />
        </div>
        <div className="explore-card-text">
          <div className="explore-card-text-name">
            <a href={url}>{name}</a>
          </div>
          <div>{desc}</div>
        </div>
      </div>
    </div>
  );
}

function ExplorePage() {
  const { currentUser } = useContext(GlobalAppContext);
  return (
    <div className="row">
      <div>
        <ExploreCard
          name="Fresh Releases"
          desc="Discover"
          img_name="fresh-releases.jpg"
          url="/explore/fresh-releases"
        />
      </div>
      <div>
        <ExploreCard
          name="Hue Sound"
          desc="Discover"
          img_name="huesound.jpg"
          url="/explore/huesound"
        />
      </div>
      <div>
        <ExploreCard
          name="Cover Art Collage"
          desc="Discover"
          img_name="cover-art-collage.jpg"
          url="/explore/cover-art-collage"
        />
      </div>
      <div>
        <ExploreCard
          name="Top Similar Users"
          desc="Social"
          img_name="similar-users.jpg"
          url="/explore/similar-users"
        />
      </div>
      {currentUser?.name && (
        <div>
          <ExploreCard
            name="Your Year in Music 2022"
            desc="Review"
            img_name="year-in-music-2022.jpg"
            url={`/user/${currentUser.name}/year-in-music/2022`}
          />
        </div>
      )}
      {currentUser?.name && (
        <div>
          <ExploreCard
            name="Your Year in Music 2021"
            desc="Review"
            img_name="year-in-music-2021.jpg"
            url={`/user/${currentUser.name}/year-in-music/2021`}
          />
        </div>
      )}
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalAppContext } = getPageProps();

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <ExplorePage />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
