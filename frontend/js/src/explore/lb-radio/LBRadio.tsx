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

// import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
// import ListenCard from "../../listens/ListenCard";
// import Card from "../../components/Card";

type PromptProps = {
  onGenerate: (prompt: string) => void;
};

type UserFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist: string;
};

function UserFeedback(props: UserFeedbackProps) {
  const { feedback } = props;

  return (
    <div className="feedback">
      <div className="feedback-header">Prompt feedback:</div>
      <ul>
        <li>Feedback #1</li>
        <li>Feedback #2</li>
        <li>Feedback #3</li>
      </ul>
    </div>
  );
}

function Playlist(props: PlaylistProps) {
  const { playlist } = props;
  return (
    <div>
      <div>Playlist item #1</div>
      <div>Playlist item #2</div>
      <div>Playlist item #3</div>
    </div>
  );
}

function Prompt(props: PromptProps) {
  const { onGenerate } = props;
  const [prompt, setPrompt] = useState<string>();

  const callbackFunction = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      console.log(event);
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      const promptText = formData.get("prompt")!;
      onGenerate(promptText);
    },
    [prompt, onGenerate]
  );

  return (
    <div className="prompt">
      <div>
        <h3>ListenBrainz Radio playlist generator</h3>
      </div>
      <form className="form form-inline" onSubmit={callbackFunction}>
        <input
          type="text"
          className="prompt-text form-control form-control-lg"
          id="prompt-input"
          placeholder="Enter prompt..."
        />
        <div className="dropdown">
          <button
            className="btn btn-lg btn-secondary dropdown-toggle"
            type="button"
            id="mode-dropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
          >
            Mode
          </button>
          <div className="dropdown-menu" aria-labelledby="mode-dropdown">
            <a className="dropdown-item" href="#">
              Easy
            </a>
            <a className="dropdown-item" href="#">
              Medium
            </a>
            <a className="dropdown-item" href="#">
              Hard
            </a>
          </div>
        </div>
        <button type="submit" className="btn btn-lg btn-primary">
          Generate
        </button>
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
  const [jspfPlaylist, setJspfPlaylist] = React.useState("");
  const [feedback, setFeedback] = React.useState([]);

  const generatePlaylistCallback = React.useCallback(
    async (prompt: string) => {
      console.log("hi mom! ", prompt);
      try {
        const request = await fetch(
          `https://api-test.listenbrainz.org/1/explore/lb-radio?prompt=${prompt}&mode=easy`
        );
        if (request.ok) {
          const payload = await request.json();
          console.log(payload.feedback);
          setJspfPlaylist(payload.jspf);
          setFeedback(payload.feedback);
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
        <Playlist playlist={jspfPlaylist} />
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
