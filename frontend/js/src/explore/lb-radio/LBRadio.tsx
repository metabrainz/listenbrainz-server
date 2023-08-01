/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import { useState } from "react";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import PlaylistItemCard from "../../playlists/PlaylistItemCard";

// import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
// import ListenCard from "../../listens/ListenCard";
// import Card from "../../components/Card";

type PromptProps = {
  onGenerate: (prompt: string, mode: string) => void;
};

type UserFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist?: JSPFPlaylist;
};

function UserFeedback(props: UserFeedbackProps) {
  const { feedback } = props;

  return (
    <div className="feedback">
      <div className="feedback-header">Prompt feedback:</div>
      <ul>
        {feedback.map((item: string) => {
          return <li key={`${item}`}>{`${item}`}</li>;
        })}
      </ul>
    </div>
  );
}

function Playlist(props: PlaylistProps) {
  const { playlist } = props;
  console.log("begin playlist ", playlist);
  if (!playlist?.track?.length) {
    console.log("playist is empty");
    return null;
  }
  return (
    <div>
      {playlist.track.map((track: JSPFTrack, index) => {
        return (
          <PlaylistItemCard
            key={`${track.id}-${index.toString()}`}
            canEdit={false}
            track={track}
            currentFeedback={0}
            updateFeedbackCallback={() => {}}
          />
        );
      })}
    </div>
  );
}

function Prompt(props: PromptProps) {
  const { onGenerate } = props;
  const [prompt, setPrompt] = useState<string>();
  const [mode, setMode] = useState<string>();

  const callbackFunction = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      const promptText = formData.get("prompt");
      const modeText = formData.get("mode");
      onGenerate((promptText as any) as string, (modeText as any) as string);
    },
    [prompt, onGenerate]
  );

  return (
    <div className="prompt">
      <div>
        <h3>ListenBrainz Radio playlist generator</h3>
      </div>
      <form onSubmit={callbackFunction}>
        <div className="input-group input-group-flex" id="prompt-input">
          <input
            type="text"
            className="form-control form-control-lg"
            name="prompt"
            placeholder="Enter prompt..."
          />
          <select className="form-control" name="mode">
            <option>easy</option>
            <option>medium</option>
            <option>hard</option>
          </select>
          <span className="input-group-btn">
            <button type="submit" className="btn btn-primary">
              Generate
            </button>
          </span>
        </div>
      </form>
      <div className="">
        <a href="https://troi.readthedocs.io/en/lb-radio/lb_radio.html">
          documentation
        </a>
      </div>
    </div>
  );
}

function LBRadio() {
  const [jspfPlaylist, setJspfPlaylist] = React.useState<JSPFObject>();
  const [feedback, setFeedback] = React.useState([]);

  const { APIService } = React.useContext(GlobalAppContext);
  const generatePlaylistCallback = React.useCallback(
    async (prompt: string, mode: string) => {
      try {
        const request = await fetch(
          `${APIService.APIBaseURI}/explore/lb-radio?prompt=${prompt}&mode=${mode}`
        );
        if (request.ok) {
          const body = await request.json();
          console.log(body.payload.jspf);
          setJspfPlaylist(body.payload.jspf);
          setFeedback(body.payload.feedback);
        }
      } catch (error) {
        console.log(error);
      }
    },
    [setJspfPlaylist, setFeedback]
  );

  return (
    <div className="row">
      <div className="col-sm-12">
        <Prompt onGenerate={generatePlaylistCallback} />
        <UserFeedback feedback={feedback} />
        <Playlist playlist={jspfPlaylist?.playlist} />
      </div>
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalAppContext } = getPageProps();

  //  const { user } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <LBRadio />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
