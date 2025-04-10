/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { faCog, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import DOMPurify from "dompurify";
import {
  Link,
  Navigate,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";

import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
} from "../playlists/utils";
import ListenControl from "../common/listens/ListenControl";
import ListenCard from "../common/listens/ListenCard";
import { ToastMsg } from "../notifications/Notifications";
import { RouteQuery } from "../utils/Loader";
import { getObjectForURLSearchParams } from "../utils/utils";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";

export type PlayerPageProps = {
  playlist?: JSPFObject;
};

type PlayerPageLoaderData = PlayerPageProps;

export interface PlayerPageState {
  playlist: JSPFPlaylist;
}

export default class PlayerPage extends React.Component<
  PlayerPageProps,
  PlayerPageState
> {
  static contextType = GlobalAppContext;

  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: PlayerPageProps) {
    super(props);

    // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
    // eslint-disable-next-line no-unused-expressions
    props.playlist?.playlist?.track?.forEach(
      (jspfTrack: JSPFTrack, index: number) => {
        // eslint-disable-next-line no-param-reassign
        jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
      }
    );
    if (props.playlist) {
      this.state = {
        playlist: props.playlist?.playlist || {},
      };
    }
  }

  getAlbumDetails(): JSX.Element {
    const { playlist } = this.state;
    return (
      <>
        <div>Release date: </div>
        <div>Label:</div>
        <div>Tags:</div>
        <div>Links:</div>
      </>
    );
  }

  savePlaylist = async () => {
    const { currentUser, APIService } = this.context;
    if (!currentUser?.auth_token) {
      return;
    }
    const { playlist } = this.props;
    if (!playlist) {
      return;
    }
    try {
      const newPlaylistId = await APIService.createPlaylist(
        currentUser.auth_token,
        playlist
      );
      toast.success(
        <ToastMsg
          title="Created playlist"
          message={
            <div>
              {" "}
              Created a new public
              <Link to={`/playlist/${newPlaylistId}/`}>instant playlist</Link>
            </div>
          }
        />,
        { toastId: "create-playlist-success" }
      );
    } catch (error) {
      toast.error(
        <ToastMsg title="Could not save playlist" message={error.message} />,
        { toastId: "create-playlist-error" }
      );
    }
  };

  handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  getHeader = (): JSX.Element => {
    const { currentUser } = this.context;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    const releaseLink =
      tracks?.[0]?.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]
        ?.release_identifier;
    const isPlayerPage = false;
    const showOptionsMenu =
      Boolean(releaseLink) || Boolean(currentUser?.auth_token);
    return (
      <div className="playlist-details row">
        <h1 className="title">
          <div>
            {playlist.title ?? "BrainzPlayer"}
            {showOptionsMenu && (
              <span className="dropdown pull-right">
                <button
                  className="btn btn-info dropdown-toggle"
                  type="button"
                  id="playlistOptionsDropdown"
                  data-toggle="dropdown"
                  aria-haspopup="true"
                  aria-expanded="true"
                >
                  <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
                  &nbsp;Options
                </button>
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="playlistOptionsDropdown"
                >
                  {releaseLink && (
                    <li>
                      See on MusicBrainz
                      <ListenControl
                        icon={faExternalLinkAlt}
                        title="Open in MusicBrainz"
                        text="Open in MusicBrainz"
                        link={releaseLink}
                        anchorTagAttributes={{
                          target: "_blank",
                          rel: "noopener noreferrer",
                        }}
                      />
                    </li>
                  )}
                  {currentUser?.auth_token && (
                    <li>
                      <a
                        id="exportPlaylistToSpotify"
                        role="button"
                        href="#"
                        onClick={this.savePlaylist}
                      >
                        Save Playlist
                      </a>
                    </li>
                  )}
                </ul>
              </span>
            )}
          </div>
        </h1>
        <div className="info">
          {tracks?.length && (
            <div>
              {tracks.length} tracks
              {isPlayerPage && (
                <>
                  {" "}
                  — Total duration:{" "}
                  {tracks
                    .filter((track) => Boolean(track?.duration))
                    .reduce(
                      (sum, { duration }) => sum + (duration as number),
                      0
                    )}
                </>
              )}
            </div>
          )}
          {isPlayerPage && this.getAlbumDetails()}
        </div>
        {playlist.annotation && (
          <div
            // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(playlist.annotation),
            }}
          />
        )}
        <hr />
      </div>
    );
  };

  render() {
    const { playlist } = this.state;

    const { track: tracks } = playlist;
    if (!playlist || !playlist.track) {
      return <div>Nothing to see here.</div>;
    }
    return (
      <div role="main">
        <div className="row">
          <div id="playlist" className="col-md-8">
            {this.getHeader()}
            <div id="listens row">
              {tracks?.map((track: JSPFTrack, index) => {
                const listen = JSPFTrackToListen(track);
                return (
                  <ListenCard
                    key={`${track.id}-${index.toString()}`}
                    listen={listen}
                    showTimestamp={false}
                    showUsername={false}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }
}

export function PlayerPageWrapper() {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObject = getObjectForURLSearchParams(searchParams);
  const location = useLocation();
  const { data } = useQuery<PlayerPageLoaderData>(
    RouteQuery(["player", searchParamsObject], location.pathname)
  );

  // BrainzPlayer
  const dispatch = useBrainzPlayerDispatch();
  const playlist = data?.playlist?.playlist;
  const { track: tracks } = playlist || {};
  React.useEffect(() => {
    const listens = tracks?.map(JSPFTrackToListen);
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listens,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tracks]);

  return <PlayerPage playlist={data?.playlist} />;
}

export function PlayerPageRedirectToAlbum() {
  const { releaseMBID } = useParams();
  return <Navigate to={`/release/${releaseMBID}`} replace />;
}
