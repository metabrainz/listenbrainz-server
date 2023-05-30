import * as React from "react";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlayCircle, faSave } from "@fortawesome/free-solid-svg-icons";
import { sanitize } from "dompurify";
import { getPlaylistExtension, getPlaylistId } from "../playlists/utils";
import { preciseTimestamp } from "../utils/utils";
import GlobalAppContext from "../utils/GlobalAppContext";

export type RecommendationPlaylistSettingsProps = {
  playlist: JSPFPlaylist;
};

export default function RecommendationPlaylistSettings({
  playlist,
}: RecommendationPlaylistSettingsProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const playlistId = getPlaylistId(playlist);
  const extension = getPlaylistExtension(playlist);
  const { track } = playlist;
  const [firstListen, ...otherListens] = track;
  const { copyPlaylist } = APIService;

  const onCopyPlaylist = React.useCallback(async (): Promise<void> => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in for this operation");
      return;
    }
    if (!playlistId?.length) {
      toast.error("No playlist to copy; missing a playlist ID");
      return;
    }
    try {
      const newPlaylistId = await copyPlaylist(
        currentUser.auth_token,
        playlistId
      );
      toast.success(
        <>
          Saved as playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
        </>
      );
    } catch (error) {
      toast.error(error.message);
    }
  }, [playlistId, currentUser, copyPlaylist]);

  const play = React.useCallback(() => {
    window.postMessage(
      { brainzplayer_event: "play-listen", payload: firstListen },
      window.location.origin
    );
  }, [firstListen]);

  return (
    <div className="playlist-settings card">
      <div className="playlist-settings-header">
        <div className="title">{playlist.title}</div>
        <div>
          {track.length} tracks | Updated {preciseTimestamp(playlist.date)}
        </div>
      </div>
      <div>
        <div className="buttons">
          <button
            className="btn btn-icon btn-info"
            onClick={play}
            type="button"
          >
            <FontAwesomeIcon icon={faPlayCircle} title="Play this playlists" />
          </button>
          <button
            className="btn btn-icon btn-info"
            onClick={onCopyPlaylist}
            type="button"
          >
            <FontAwesomeIcon icon={faSave} title="Save to my playlists" />
          </button>
        </div>
        <div>
          {extension?.public ? "Public" : "Pr	ivate"} playlist by&nbsp;
          {playlist.creator} | For {extension?.collaborators[0]}
        </div>
        <hr />
        {playlist.annotation && (
          <>
            <div
              // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{
                __html: sanitize(playlist.annotation),
              }}
            />
            {/* <hr /> */}
          </>
        )}
      </div>
    </div>
  );
}
