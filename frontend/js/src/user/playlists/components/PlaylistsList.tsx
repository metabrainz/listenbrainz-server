import { noop } from "lodash";
import * as React from "react";
import PlaylistCard from "./PlaylistCard";
import { PlaylistType } from "../../../playlists/utils";
import PlaylistView from "../playlistView.d";
import Pagination from "../../../common/Pagination";

export type PlaylistsListProps = {
  playlists: JSPFPlaylist[];
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

export default function PlaylistsList(
  props: PlaylistsListProps & { children: React.ReactNode }
) {
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
  } = props;

  return (
    <div>
      {!playlists.length && <p>No playlists to show yet. Come back later !</p>}
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
              index={index + (page - 1) * 25}
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
