/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import { get, has } from "lodash";
import { getPageProps } from "../utils/utils";

import ErrorBoundary from "../utils/ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import SimpleModal from "../utils/SimpleModal";
import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";

type ExplorePageProps = {
  name: string;
  desc: string;
  img_name: string;
  url: string;
};

function ExploreIndex(props: ExplorePageProps) {
  const { name, desc, img_name, url } = props;
  return (
    <div className="explore-card">
      <img src={`/static/img/explore/${img_name}`} alt={name} />
      <h3>{name}</h3>
      <p>{desc}</p>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const modalRef = React.createRef<SimpleModal>();
  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
    modal: modalRef,
  };

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <div className="row">
          <div className="col-md-4">
            <ExploreIndex
              name="Fresh Releases"
              desc="Discover"
              img_name="fresh-releases.png"
              url="/explore/fresh-releases"
            />
          </div>
          <div className="col-md-4">
            <ExploreIndex
              name="Hue Sound"
              desc="Discover"
              img_name="huesound.png"
              url="/explore/huesound"
            />
          </div>
          <div className="col-md-4">
            <ExploreIndex
              name="Cover Art Collage"
              desc="Discover"
              img_name="cover-art-collage.png"
              url="/explore/cover-art-collage"
            />
          </div>
        </div>
        <div className="row">
          <div className="col-md-4">
            <ExploreIndex
              name="Top Similar Users"
              desc="Social"
              img_name="similar-users.png"
              url="/explore/similar-users"
            />
          </div>
          {current_user?.name && (
            <div className="col-md-4">
              <ExploreIndex
                name="Your Year in Music"
                desc="Review"
                img_name="year-in-music.png"
                url="/user/rob/year-in-music"
              />
            </div>
          )}
        </div>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
