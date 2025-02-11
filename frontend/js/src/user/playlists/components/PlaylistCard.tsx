/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import {
  faCog,
  faSave,
  faCalendar,
  faMusic,
  faEllipsisVertical,
} from "@fortawesome/free-solid-svg-icons";

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { sanitize } from "dompurify";
import { toast } from "react-toastify";
import { Link, useNavigate } from "react-router-dom";
import Card from "../../../components/Card";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import PlaylistMenu from "../../../playlists/components/PlaylistMenu";
import { getPlaylistExtension, getPlaylistId } from "../../../playlists/utils";
import PlaylistView from "../playlistView.d";

export type PlaylistCardProps = {
  playlist: JSPFPlaylist;
  onSuccessfulCopy: (playlist: JSPFPlaylist) => void;
  onPlaylistEdited: (playlist: JSPFPlaylist) => void;
  onPlaylistDeleted: (playlist: JSPFPlaylist) => void;
  showOptions: boolean;
  view: PlaylistView;
  index: number;
};

export default function PlaylistCard({
  playlist,
  view,
  index,
  onSuccessfulCopy,
  onPlaylistEdited,
  onPlaylistDeleted,
  showOptions = true,
}: PlaylistCardProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const { copyPlaylist, getPlaylist, getPlaylistImage } = APIService;
  const navigate = useNavigate();

  const [playlistImageString, setPlaylistImageString] = React.useState<
    string
  >();

  const playlistId = getPlaylistId(playlist);
  const customFields = getPlaylistExtension(playlist);

  const onCopyPlaylist = React.useCallback(
    async (evt: React.MouseEvent): Promise<void> => {
      evt.preventDefault();
      if (!currentUser?.auth_token) {
        toast.error(
          <ToastMsg
            title="Error"
            message="You must be logged in for this operation"
          />,
          { toastId: "auth-error" }
        );

        return;
      }
      if (!playlistId?.length) {
        toast.error(
          <ToastMsg
            title="Error"
            message="No playlist to copy; missing a playlist ID"
          />,
          { toastId: "copy-playlist-error" }
        );
        return;
      }
      try {
        const newPlaylistId = await copyPlaylist(
          currentUser.auth_token,
          playlistId
        );
        // Fetch the newly created playlist and add it to the state if it's the current user's page
        const JSPFObject: JSPFObject = await getPlaylist(
          newPlaylistId,
          currentUser.auth_token
        ).then((res) => res.json());
        toast.success(
          <ToastMsg
            title="Duplicated playlist"
            message={
              <>
                Duplicated to playlist&ensp;
                <Link to={`/playlist/${newPlaylistId}/`}>
                  {JSPFObject.playlist.title}
                </Link>
              </>
            }
          />,
          { toastId: "copy-playlist-success" }
        );

        onSuccessfulCopy(JSPFObject.playlist);
      } catch (error) {
        toast.error(<ToastMsg title="Error" message={error.message} />, {
          toastId: "copy-playlist-error",
        });
      }
    },
    [
      currentUser.auth_token,
      playlistId,
      copyPlaylist,
      getPlaylist,
      onSuccessfulCopy,
    ]
  );

  const navigateToPlaylist = () => {
    navigate(`/playlist/${sanitize(playlistId)}/`);
  };

  React.useEffect(() => {
    const fetchCoverArtImage = async () => {
      const savedLayout = customFields?.additional_metadata?.cover_art;
      const svgString = await getPlaylistImage(
        playlistId,
        currentUser?.auth_token!,
        savedLayout?.dimension,
        savedLayout?.layout
      );
      setPlaylistImageString(svgString);
    };
    // Only fetch the image in grid view and if user is logged in (requires auth token for playlist privacy check)
    if (view === PlaylistView.GRID && currentUser?.auth_token) {
      fetchCoverArtImage().catch((error) => {
        // eslint-disable-next-line no-console
        console.error(error);
        // setPlaylistImageString("");
      });
    }
  }, [
    view,
    playlistId,
    customFields?.additional_metadata?.cover_art,
    currentUser?.auth_token,
    getPlaylistImage,
  ]);

  if (view === PlaylistView.LIST) {
    return (
      <div className="playlist-card-list-view">
        <div
          className="playlist-card-container"
          onClick={navigateToPlaylist}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              navigateToPlaylist();
            }
          }}
          role="presentation"
        >
          <div className="playlist-info">
            <div className="playlist-index">{index + 1}</div>
            <div className="playlist-info-content">
              <div className="playlist-title">
                <Link to={`/playlist/${sanitize(playlistId)}/`}>
                  {playlist.title}
                </Link>
              </div>
              {playlist.annotation && (
                <div
                  className="description"
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{ __html: playlist.annotation }}
                />
              )}
            </div>
          </div>
          <div className="playlist-more-info">
            <div className="playlist-stats">
              <div className="playlist-date">
                <FontAwesomeIcon icon={faCalendar} />
                {new Date(playlist.date).toLocaleString(undefined, {
                  dateStyle: "short",
                })}
              </div>
              <div className="playlist-date">
                <FontAwesomeIcon icon={faMusic} />
                {playlist.track?.length} track
                {playlist.track?.length === 1 ? "" : "s"}
              </div>
            </div>
          </div>
        </div>
        <div className="playlist-actions dropdown playlist-card-action-dropdown">
          <FontAwesomeIcon
            icon={faEllipsisVertical}
            fixedWidth
            id="playlistOptionsDropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
            type="button"
          />
          {showOptions ? (
            <PlaylistMenu
              playlist={playlist}
              onPlaylistSaved={onPlaylistEdited}
              onPlaylistDeleted={onPlaylistDeleted}
              onPlaylistCopied={onSuccessfulCopy}
            />
          ) : (
            <ul
              className="dropdown-menu dropdown-menu-right"
              aria-labelledby="playlistOptionsDropdown"
            >
              <li>
                <a onClick={onCopyPlaylist} role="button" href="#">
                  <FontAwesomeIcon
                    fixedWidth
                    icon={faSave as IconProp}
                    title="Save to my playlists"
                  />
                  &nbsp;Save
                </a>
              </li>
            </ul>
          )}
        </div>
      </div>
    );
  }
  const dateToDisplay = new Date(
    customFields?.last_modified_at ?? playlist.date
  ).toLocaleString(undefined, {
    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
    dateStyle: "short",
  });

  return (
    <Card className="playlist" key={playlistId}>
      <Link to={`/playlist/${sanitize(playlistId)}/`}>
        <div
          className="cover-art"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html:
              playlistImageString ??
              "<img src='/static/img/cover-art-placeholder.jpg'></img>",
          }}
          title={`Cover art for ${playlist.title}`}
        />
        <div className="info">
          <div className="ellipsis-2-lines mt-5 mb-10">{playlist.title}</div>
          <small>
            {playlist.track.length} track{playlist.track.length > 1 && "s"}
            <br />
            <span className="help-block">Last modified: {dateToDisplay}</span>
          </small>
        </div>
      </Link>
      {!showOptions ? (
        <button
          className="playlist-card-action-button btn btn-info"
          onClick={onCopyPlaylist}
          type="button"
        >
          <FontAwesomeIcon
            fixedWidth
            icon={faSave as IconProp}
            title="Save to my playlists"
          />
        </button>
      ) : (
        <div className="dropup playlist-card-action-dropdown">
          <button
            className="dropdown-toggle playlist-card-action-button btn btn-info"
            type="button"
            id="playlistOptionsDropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
          >
            <FontAwesomeIcon
              icon={faCog as IconProp}
              fixedWidth
              title="More options"
            />
          </button>
          <PlaylistMenu
            playlist={playlist}
            onPlaylistSaved={onPlaylistEdited}
            onPlaylistDeleted={onPlaylistDeleted}
            onPlaylistCopied={onSuccessfulCopy}
          />
        </div>
      )}
    </Card>
  );
}
