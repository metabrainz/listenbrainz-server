/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCog, faFileExport } from "@fortawesome/free-solid-svg-icons";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import PlaylistItemCard from "../../playlists/PlaylistItemCard";
import Loader from "../../components/Loader";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import { JSPFTrackToListen } from "../../playlists/utils";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";

type LBRadioProps = {
  userArg: string;
  modeArg: string;
  promptArg: string;
};

type PromptProps = {
  onGenerate: (prompt: string, mode: string) => void;
  errorMessage: string;
  initMode: string;
  initPrompt: string;
};

type UserFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist?: JSPFPlaylist;
  title: string;
};

function UserFeedback(props: UserFeedbackProps) {
  const { feedback } = props;

  if (feedback.length === 0) {
    return <div className="feedback" />;
  }

  return (
    <div id="feedback" className="alert alert-info">
      <div className="feedback-header">Query feedback:</div>
      <ul>
        {feedback.map((item: string) => {
          return <li key={`${item}`}>{`${item}`}</li>;
        })}
      </ul>
    </div>
  );
}

function Playlist(props: PlaylistProps) {
  const { playlist, title } = props;
  // TODO: Work out how to connect this
  const showSpotifyExportButton = true;
  if (!playlist?.track?.length) {
    return null;
  }
  return (
    <div>
      <div id="playlist-title">
        <span className="dropdown pull-right">
          <button
            className="btn btn-info dropdown-toggle"
            type="button"
            id="options-dropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
          >
            <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
            &nbsp;Options
          </button>
          <ul
            className="dropdown-menu dropdown-menu-right"
            aria-labelledby="options-dropdown"
          >
            <li>
              <a role="button" href="#">
                Save
              </a>
            </li>
            {showSpotifyExportButton && (
              <>
                <li role="separator" className="divider" />
                <li>
                  <a id="exportPlaylistToSpotify" role="button" href="#">
                    <FontAwesomeIcon icon={faSpotify as IconProp} /> Export to
                    Spotify
                  </a>
                </li>
              </>
            )}
            <li role="separator" className="divider" />
            <li>
              <a id="exportPlaylistToJSPF" role="button" href="#">
                <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as
                JSPF
              </a>
            </li>
          </ul>
        </span>
        <div id="title">{title}</div>
      </div>
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
    </div>
  );
}

function Prompt(props: PromptProps) {
  const { onGenerate, errorMessage, initMode, initPrompt } = props;
  const [prompt, setPrompt] = useState<string>(initPrompt);
  const [mode, setMode] = useState<string>(initMode);
  const [hideExamples, setHideExamples] = React.useState(false);

  const generateCallbackFunction = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      const modeText = formData.get("mode");
      setHideExamples(true);
      onGenerate(prompt, (modeText as any) as string);
    },
    [prompt, onGenerate, hideExamples]
  );

  const onInputChangeCallback = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const text = event.target.value;
      setPrompt(text);
    },
    []
  );

  React.useEffect(() => {
    if (prompt.length > 0) {
      setHideExamples(true);
      onGenerate(initPrompt, initMode);
    }
  }, []);

  return (
    <div className="prompt">
      <div>
        <h3>
          ListenBrainz Radio playlist generator
          <small>
            <a
              id="doc-link"
              href="https://troi.readthedocs.io/en/add-user-stats-entity/lb_radio.html"
            >
              How do I write a query?
            </a>
          </small>
        </h3>
      </div>
      <form onSubmit={generateCallbackFunction}>
        <div className="input-group input-group-flex" id="prompt-input">
          <input
            type="text"
            className="form-control form-control-lg"
            name="prompt"
            value={prompt}
            placeholder="Enter prompt..."
            onChange={onInputChangeCallback}
          />
          <select
            className="form-control"
            id="mode-dropdown"
            name="mode"
            defaultValue={mode}
          >
            <option value="easy">easy</option>
            <option value="medium">medium</option>
            <option value="hard">hard</option>
          </select>
          <span className="input-group-btn">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={prompt?.length <= 3}
            >
              Generate
            </button>
          </span>
        </div>
      </form>
      {hideExamples === false && (
        <div id="examples">
          Examples:
          <a href="/explore/lb-radio?prompt=artist:(radiohead)&mode=easy">
            artist:(radiohead)
          </a>
          <a href="/explore/lb-radio?prompt=tag:(trip hop)&mode=easy">
            tag:(trip hop)
          </a>
          <a href="/explore/lb-radio?prompt=%23metal&mode=easy">#metal</a>
          <a href="/explore/lb-radio?prompt=user:rob&mode=easy">user:rob</a>
        </div>
      )}
      {errorMessage.length > 0 && (
        <div id="error-message" className="alert alert-danger">
          {errorMessage}
        </div>
      )}
    </div>
  );
}

function LBRadio(props: LBRadioProps) {
  const { userArg, modeArg, promptArg } = props;
  const [jspfPlaylist, setJspfPlaylist] = React.useState<JSPFObject>();
  const [feedback, setFeedback] = React.useState([]);
  const [isLoading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [title, setTitle] = useState<string>("");

  const { APIService } = React.useContext(GlobalAppContext);
  const generatePlaylistCallback = React.useCallback(
    async (prompt: string, mode: string) => {
      setErrorMessage("");
      setLoading(true);
      try {
        const request = await fetch(
          `${APIService.APIBaseURI}/explore/lb-radio?prompt=${prompt}&mode=${mode}`
        );
        if (request.ok) {
          const body = await request.json();
          setJspfPlaylist(body.payload.jspf);
          setFeedback(body.payload.feedback);
          setTitle(body.payload.jspf.playlist.annotation);
        } else {
          const msg = await request.json();
          setErrorMessage(msg.error);
        }
      } catch (error) {
        setErrorMessage(error);
      }
      setLoading(false);
    },
    [setJspfPlaylist, setFeedback]
  );

  return (
    <>
      <div className="row">
        <div className="col-sm-12">
          <Prompt
            onGenerate={generatePlaylistCallback}
            errorMessage={errorMessage}
            initPrompt={promptArg}
            initMode={modeArg}
          />
          <Loader
            isLoading={isLoading}
            loaderText="Generating playlist…"
            className="playlist-loader"
          >
            <UserFeedback feedback={feedback} />
            <Playlist playlist={jspfPlaylist?.playlist} title={title} />
          </Loader>
        </div>
      </div>
      <BrainzPlayer
        listens={jspfPlaylist?.playlist.track.map(JSPFTrackToListen) ?? []}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
      />
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalAppContext } = getPageProps();

  const { user, mode, prompt } = reactProps;
  const renderRoot = createRoot(domContainer!);
  const LBRadioWithAlertNotifications = withAlertNotifications(LBRadio);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <LBRadioWithAlertNotifications
            userArg={user}
            modeArg={mode}
            promptArg={prompt}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});