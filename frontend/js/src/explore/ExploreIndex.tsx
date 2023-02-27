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

function ExploreIndex() {
  return (
    <div className="explore-card">
      <h3>Explore card title</h3>
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
        <ExploreIndex />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
