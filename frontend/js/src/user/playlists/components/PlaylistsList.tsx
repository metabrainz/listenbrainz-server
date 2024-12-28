/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import { noop } from "lodash";
import * as React from "react";
import { toast } from "react-toastify";
import Loader from "../../../components/Loader";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import PlaylistCard from "./PlaylistCard";
import { PlaylistType } from "../../../playlists/utils";
import PlaylistView from "../playlistView.d";
import Pagination from "../../../common/Pagination";

export type PlaylistsListProps = {
  playlists: JSPFPlaylist[];
  user: ListenBrainzUser;
  pageCount: number;
  page: number;
  activeSection: PlaylistType;
  view: PlaylistView;
  onCopiedPlaylist?: (playlist: JSPFPlaylist) => void;
  onPlaylistEdited: (playlist: JSPFPlaylist) => void;
  onPlaylistDeleted: (playlist: JSPFPlaylist) => void;
  handleClickPrevious: () => void;
  handleClickNext: () => void;
};

export type PlaylistsListState = {
  loading: boolean;
  paginationOffset: number;
  playlistCount: number;
};

export default class PlaylistsList extends React.Component<
  React.PropsWithChildren<PlaylistsListProps>
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  alertNotAuthorized = () => {
    toast.error(
      <ToastMsg
        title="Not allowed"
        message="You are not authorized to modify this playlist"
      />,
      { toastId: "auth-error" }
    );
  };

  isCurrentUserPage = () => {
    const { user, activeSection } = this.props;
    const { currentUser } = this.context;
    if (activeSection === PlaylistType.recommendations) {
      return false;
    }
    return currentUser?.name === user.name;
  };

  render() {
    const {
      playlists,
      activeSection,
      children,
      view,
      page,
      pageCount,
      onCopiedPlaylist,
      onPlaylistEdited,
      onPlaylistDeleted,
      handleClickPrevious,
      handleClickNext,
    } = this.props;
    return (
      <div>
        {!playlists.length && (
          <p>No playlists to show yet. Come back later !</p>
        )}
        <div
          id="playlists-container"
          className={view === PlaylistView.LIST ? "list-view" : ""}
        >
          {playlists.map((playlist: JSPFPlaylist, index: number) => {
            return (
              <PlaylistCard
                view={view}
                showOptions={activeSection !== PlaylistType.recommendations}
                playlist={playlist}
                onSuccessfulCopy={onCopiedPlaylist ?? noop}
                onPlaylistEdited={onPlaylistEdited}
                onPlaylistDeleted={onPlaylistDeleted}
                key={playlist.identifier}
                index={index}
              />
            );
          })}
          {children}
        </div>
        <Pagination
          currentPageNo={page}
          totalPageCount={pageCount}
          handleClickPrevious={handleClickPrevious}
          handleClickNext={handleClickNext}
        />
      </div>
    );
  }
}
