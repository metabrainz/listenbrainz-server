/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCog, faFileExport } from "@fortawesome/free-solid-svg-icons";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import { toast } from "react-toastify";
import { saveAs } from "file-saver";
import { get, set } from "lodash";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import PlaylistItemCard from "../../playlists/PlaylistItemCard";
import Loader from "../../components/Loader";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
} from "../../playlists/utils";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import { ToastMsg } from "../../notifications/Notifications";

type LBRadioProps = {
  userArg: string;
  modeArg: string;
  promptArg: string;
  authToken: string;
  enableOptions: boolean;
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
  onSavePlaylist: () => void;
  enableOptions: boolean;
  onSaveToSpotify: () => void;
  onExportJSPF: () => void;
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
  const {
    playlist,
    title,
    onSavePlaylist,
    enableOptions,
    onSaveToSpotify,
    onExportJSPF,
  } = props;
  const { spotifyAuth } = React.useContext(GlobalAppContext);
  const showSpotifyExportButton = spotifyAuth?.permission?.includes(
    "playlist-modify-public"
  );
  if (!playlist?.track?.length) {
    return null;
  }
  return (
    <div>
      <div id="playlist-title">
        {enableOptions && (
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
                <a onClick={onSavePlaylist} role="button" href="#">
                  Save
                </a>
              </li>
              {showSpotifyExportButton && (
                <>
                  <li role="separator" className="divider" />
                  <li>
                    <a
                      onClick={onSaveToSpotify}
                      id="exportPlaylistToSpotify"
                      role="button"
                      href="#"
                    >
                      <FontAwesomeIcon icon={faSpotify as IconProp} /> Export to
                      Spotify
                    </a>
                  </li>
                </>
              )}
              <li role="separator" className="divider" />
              <li>
                <a
                  onClick={onExportJSPF}
                  id="exportPlaylistToJSPF"
                  role="button"
                  href="#"
                >
                  <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as
                  JSPF
                </a>
              </li>
            </ul>
          </span>
        )}
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
        <div>
          <div id="examples">
            Examples:
            <a href="/explore/lb-radio?prompt=artist:(radiohead)&mode=easy">
              artist:(radiohead)
            </a>
            <a href="/explore/lb-radio?prompt=tag:(trip hop)&mode=easy">
              tag:(trip hop)
            </a>
            <a href="/explore/lb-radio?prompt=%23metal&mode=easy">#metal</a>
            <a href="/explore/lb-radio?prompt=stats:rob&mode=easy">stats:rob</a>
          </div>
          <div id="made-with-postgres">
            <img
              src="/static/img/explore/made-with-postgres.png"
              alt="Made with Postgres, not AI!"
            />
          </div>
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
  const { userArg, modeArg, promptArg, authToken, enableOptions } = props;
  const [jspfPlaylist, setJspfPlaylist] = React.useState<JSPFObject>();
  const [feedback, setFeedback] = React.useState<string[]>([]);
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
          const body: {
            payload: { jspf: JSPFObject; feedback: string[] };
          } = await request.json();
          const { payload } = body;
          const { playlist } = payload?.jspf as JSPFObject;
          if (playlist?.track?.length) {
            // Augment track with metadata fetched from LB server, mainly so we can have cover art
            try {
              const recordingMetadataMap = await APIService.getRecordingMetadata(
                playlist.track.map(getRecordingMBIDFromJSPFTrack)
              );
              if (recordingMetadataMap) {
                playlist?.track.forEach((track) => {
                  const mbid = getRecordingMBIDFromJSPFTrack(track);
                  if (recordingMetadataMap[mbid]) {
                    const additionalMetadata = get(
                      track,
                      `extension.[${MUSICBRAINZ_JSPF_TRACK_EXTENSION}].additional_metadata`,
                      {}
                    );
                    additionalMetadata.caa_id =
                      recordingMetadataMap[mbid].release?.caa_id;
                    additionalMetadata.caa_release_mbid =
                      recordingMetadataMap[mbid].release?.caa_release_mbid;

                    set(
                      track,
                      `extension.[${MUSICBRAINZ_JSPF_TRACK_EXTENSION}].additional_metadata`,
                      additionalMetadata
                    );
                  }
                });
              }
            } catch (error) {
              // Don't do anything about this error, it's just metadata augmentation
              // eslint-disable-next-line no-console
              console.error(error);
            }
          }
          setJspfPlaylist(payload.jspf);
          setFeedback(payload.feedback);
          setTitle(payload.jspf?.playlist?.annotation ?? "");
        } else {
          const msg = await request.json();
          setErrorMessage(msg?.error);
        }
      } catch (error) {
        setErrorMessage(error);
      }
      setLoading(false);
    },
    [setJspfPlaylist, setFeedback]
  );

  const onSavePlaylist = React.useCallback(async () => {
    // TODO: Move the guts of this to APIService
    const args = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${authToken}`,
      },
      body: JSON.stringify(jspfPlaylist),
    };
    try {
      const request = await fetch(
        `${APIService.APIBaseURI}/playlist/create`,
        args
      );
      if (request.ok) {
        const { playlist_mbid } = await request.json();
        toast.success(
          <ToastMsg
            title="Saved playlist"
            message={
              <>
                Playlist saved to &ensp;
                <a href={`/playlist/${playlist_mbid}`}>
                  {jspfPlaylist?.playlist.title}
                </a>
              </>
            }
          />,
          { toastId: "saved-playlist" }
        );
      } else {
        const { error } = await request.json();
        toast.error(
          <ToastMsg
            title="Error"
            message={`Failed to save playlist: ${error}.`}
          />,
          { toastId: "saved-playlist-error" }
        );
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to save playlist: ${error}.`}
        />,
        { toastId: "saved-playlist-error" }
      );
    }
  }, [jspfPlaylist]);

  const onSaveToSpotify = React.useCallback(async () => {
    // TODO: Move the guts of this to APIService
    const args = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${authToken}`,
      },
      body: JSON.stringify(jspfPlaylist),
    };
    const playlistTitle = jspfPlaylist?.playlist.title;
    try {
      const request = await fetch(
        `${APIService.APIBaseURI}/playlist/export-jspf/spotify`,
        args
      );
      if (request.ok) {
        const { external_url } = await request.json();
        toast.success(
          <ToastMsg
            title="Saved playlist"
            message={
              <>
                Successfully exported playlist:{" "}
                <a
                  href={external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {playlistTitle}
                </a>
                Heads up: the new playlist is public on Spotify.
              </>
            }
          />,
          { toastId: "saved-playlist" }
        );
      } else {
        const { error } = await request.json();
        toast.error(
          <ToastMsg
            title="Error"
            message={`Failed to save playlist to Spotify: ${error}.`}
          />,
          { toastId: "saved-playlist-error" }
        );
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to save playlist to Spotify: ${error}.`}
        />,
        { toastId: "saved-playlist-error" }
      );
    }
  }, [jspfPlaylist]);

  const onExportJSPF = React.useCallback(async () => {
    const jspf = new Blob([JSON.stringify(jspfPlaylist)], {
      type: "application/json;charset=utf-8",
    });
    saveAs(jspf, `${title}.jspf`);
  }, [jspfPlaylist, title]);

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
            <Playlist
              playlist={jspfPlaylist?.playlist}
              title={title}
              onSavePlaylist={onSavePlaylist}
              enableOptions={enableOptions}
              onSaveToSpotify={onSaveToSpotify}
              onExportJSPF={onExportJSPF}
            />
          </Loader>
        </div>
      </div>
      <BrainzPlayer
        listens={jspfPlaylist?.playlist?.track?.map(JSPFTrackToListen) ?? []}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
      />
    </>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalAppContext } = getPageProps();

  const { user, mode, prompt, token } = reactProps;
  const renderRoot = createRoot(domContainer!);
  const LBRadioWithAlertNotifications = withAlertNotifications(LBRadio);

  const enableOptions = token !== "";
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <LBRadioWithAlertNotifications
            userArg={user}
            modeArg={mode}
            promptArg={prompt}
            authToken={token}
            enableOptions={enableOptions}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
