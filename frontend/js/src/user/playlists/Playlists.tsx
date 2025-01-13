import {
  faListAlt,
  faPlusCircle,
  faUsers,
  faFileImport,
} from "@fortawesome/free-solid-svg-icons";
import { faSpotify, faItunesNote } from "@fortawesome/free-brands-svg-icons";
import * as React from "react";

import { orderBy } from "lodash";
import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLoaderData, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import Card from "../../components/Card";
import Pill from "../../components/Pill";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import ImportPlaylistModal from "./components/ImportJSPFPlaylistModal";
import ImportSpotifyPlaylistModal from "./components/ImportSpotifyPlaylistModal";
import ImportAppleMusicPlaylistModal from "./components/ImportAppleMusicPlaylistModal";
import PlaylistsList from "./components/PlaylistsList";
import {
  getPlaylistExtension,
  getPlaylistId,
  PlaylistType,
} from "../../playlists/utils";
import PlaylistView from "./playlistView.d";
import { faGrid, faStacked } from "../../utils/icons";
import { getObjectForURLSearchParams } from "../../utils/utils";

export type UserPlaylistsProps = {
  playlists: JSPFObject[];
  user: ListenBrainzUser;
  playlistCount: number;
  pageCount: number;
};

export type UserPlaylistsState = {
  playlists: JSPFPlaylist[];
  sortBy: SortOption;
  view: PlaylistView;
};

enum SortOption {
  DATE_CREATED = "dateCreated",
  DATE_UPDATED = "dateUpdated",
  TITLE = "title",
  CREATOR = "creator",
  RANDOM = "random",
}

type UserPlaylistsLoaderData = UserPlaylistsProps;

type UserPlaylistsClassProps = UserPlaylistsProps & {
  page: number;
  playlistType: PlaylistType;
  handleClickPrevious: () => void;
  handleClickNext: () => void;
  handleSetPlaylistType: (newType: PlaylistType) => void;
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsClassProps,
  UserPlaylistsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserPlaylistsClassProps) {
    super(props);
    const { playlists, playlistCount } = props;
    this.state = {
      playlists: playlists?.map((pl) => pl.playlist) ?? [],
      sortBy: SortOption.DATE_CREATED,
      view: PlaylistView.GRID,
    };
  }

  componentDidUpdate(prevProps: Readonly<UserPlaylistsClassProps>): void {
    const { playlists } = this.props;
    if (prevProps.playlists !== playlists) {
      this.setState({ playlists: playlists.map((pl) => pl.playlist) });
    }
  }

  alertNotAuthorized = () => {
    toast.error(
      <ToastMsg
        title="Not allowed"
        message="You are not authorized to modify this playlist"
      />,
      { toastId: "auth-error" }
    );
  };

  setPlaylistType = (type: PlaylistType) => {
    const { handleSetPlaylistType, playlistType } = this.props;
    if (type !== playlistType) {
      handleSetPlaylistType(type);
      this.setState({ sortBy: SortOption.DATE_CREATED });
    }
  };

  onCopiedPlaylist = (newPlaylist: JSPFPlaylist): void => {
    const { playlistType } = this.props;
    if (this.isCurrentUserPage() && playlistType === PlaylistType.playlists) {
      this.setState((prevState) => ({
        playlists: [newPlaylist, ...prevState.playlists],
      }));
    }
  };

  onPlaylistEdited = async (playlist: JSPFPlaylist): Promise<void> => {
    // Once API call succeeds, update playlist in state
    const { playlists } = this.state;
    const playlistsCopy = [...playlists];
    const playlistIndex = playlistsCopy.findIndex(
      (pl) => getPlaylistId(pl) === getPlaylistId(playlist)
    );
    playlistsCopy[playlistIndex] = playlist;
    this.setState({
      playlists: playlistsCopy,
    });
  };

  onPlaylistCreated = async (playlist: JSPFPlaylist): Promise<void> => {
    const { playlists } = this.state;
    this.setState({
      playlists: [playlist, ...playlists],
    });
  };

  onPlaylistDeleted = (deletedPlaylist: JSPFPlaylist): void => {
    this.setState((prevState) => ({
      playlists: prevState.playlists?.filter(
        (pl) => getPlaylistId(pl) !== getPlaylistId(deletedPlaylist)
      ),
    }));
  };

  alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  isCurrentUserPage = () => {
    const { user } = this.props;
    const { currentUser } = this.context;
    return currentUser?.name === user.name;
  };

  setSortOption = (option: SortOption) => {
    const { playlists } = this.state;
    if (option === SortOption.RANDOM) {
      this.setState({
        sortBy: option,
        playlists: [...playlists].sort(() => Math.random() - 0.5),
      });
      return;
    }

    const sortPlaylists = (criteria: any, orders: any) =>
      orderBy([...playlists], criteria, orders);

    const criterias = {
      [SortOption.DATE_CREATED]: (pl: JSPFPlaylist) =>
        new Date(pl.date).getTime(),
      [SortOption.TITLE]: (pl: JSPFPlaylist) => pl.title.toLowerCase(),
      [SortOption.CREATOR]: (pl: JSPFPlaylist) => pl.creator.toLowerCase(),
      [SortOption.DATE_UPDATED]: (pl: JSPFPlaylist) =>
        getPlaylistExtension(pl)?.last_modified_at || pl.date,
    };

    const orders = {
      [SortOption.DATE_CREATED]: ["desc"],
      [SortOption.TITLE]: ["asc"],
      [SortOption.CREATOR]: ["asc"],
      [SortOption.DATE_UPDATED]: ["desc"],
    };

    const sortingCriteriaBasedOnOption = [
      criterias[option as keyof typeof criterias],
      ...Object.values(criterias).filter(
        (c) => c !== criterias[option as keyof typeof criterias]
      ),
    ];

    const sortingOrdersBasedOnOption = [
      orders[option],
      ...Object.values(orders).filter((o) => o !== orders[option]),
    ];

    const sortedPlaylists = sortPlaylists(
      sortingCriteriaBasedOnOption,
      sortingOrdersBasedOnOption
    );

    this.setState({
      sortBy: option,
      playlists: sortedPlaylists,
    });
  };

  render() {
    const {
      user,
      pageCount,
      page,
      playlistType,
      handleClickPrevious,
      handleClickNext,
    } = this.props;
    const { playlists, sortBy, view } = this.state;
    const { currentUser } = this.context;

    return (
      <div role="main" id="playlists-page">
        <Helmet>
          <title>{`${
            user?.name === currentUser?.name ? "Your" : `${user?.name}'s`
          } Playlists`}</title>
        </Helmet>
        <div className="tertiary-nav">
          <div className="playlist-view-options">
            <div className="playlist-view-controls">
              <Pill
                active={playlistType === PlaylistType.playlists}
                type="secondary"
                onClick={() => this.setPlaylistType(PlaylistType.playlists)}
              >
                <FontAwesomeIcon icon={faListAlt as IconProp} /> Playlists
              </Pill>
              <Pill
                active={playlistType === PlaylistType.collaborations}
                type="secondary"
                onClick={() =>
                  this.setPlaylistType(PlaylistType.collaborations)
                }
              >
                <FontAwesomeIcon icon={faUsers as IconProp} /> Collaborative
              </Pill>
            </div>
            <div className="playlist-view-controls">
              <Pill
                active={view === PlaylistView.GRID}
                type="secondary"
                onClick={() => this.setState({ view: PlaylistView.GRID })}
                title="Grid view"
              >
                <FontAwesomeIcon icon={faGrid} fixedWidth />
              </Pill>
              <Pill
                active={view === PlaylistView.LIST}
                type="secondary"
                onClick={() => this.setState({ view: PlaylistView.LIST })}
                title="List view"
              >
                <FontAwesomeIcon icon={faStacked} fixedWidth />
              </Pill>
            </div>
          </div>
          <div className="playlist-view-options">
            <div className="playlist-sort-controls">
              <b>Sort by:</b>
              <select
                value={sortBy}
                onChange={(e) =>
                  this.setSortOption(e.target.value as SortOption)
                }
                className="form-control"
                style={{ width: "200px" }}
              >
                <option value={SortOption.DATE_CREATED}>Date Created</option>
                <option value={SortOption.DATE_UPDATED}>Date Updated</option>
                <option value={SortOption.TITLE}>Title</option>
                <option value={SortOption.CREATOR}>Creator</option>
                <option value={SortOption.RANDOM}>Random</option>
              </select>
            </div>
            {this.isCurrentUserPage() && (
              <div className="dropdown">
                <button
                  className="btn btn-info dropdown-toggle"
                  type="button"
                  id="ImportPlaylistDropdown"
                  data-toggle="dropdown"
                  aria-haspopup="true"
                >
                  <FontAwesomeIcon icon={faPlusCircle} title="Import" />
                  &nbsp;Import&nbsp;
                  <span className="caret" />
                </button>
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="ImportPlaylistDropdown"
                >
                  <li>
                    <button
                      type="button"
                      onClick={() => {
                        NiceModal.show<JSPFPlaylist | JSPFPlaylist[], any>(
                          ImportSpotifyPlaylistModal
                        ).then((playlist) => {
                          if (Array.isArray(playlist)) {
                            playlist.forEach((p: JSPFPlaylist) => {
                              this.onPlaylistCreated(p);
                            });
                          } else {
                            this.onPlaylistCreated(playlist);
                          }
                        });
                      }}
                      data-toggle="modal"
                      data-target="#ImportMusicServicePlaylistModal"
                    >
                      <FontAwesomeIcon icon={faSpotify} />
                      &nbsp;Spotify
                    </button>
                  </li>
                  <li>
                    <button
                      type="button"
                      onClick={() => {
                        NiceModal.show<JSPFPlaylist | JSPFPlaylist[], any>(
                          ImportAppleMusicPlaylistModal
                        ).then((playlist) => {
                          if (Array.isArray(playlist)) {
                            playlist.forEach((p: JSPFPlaylist) => {
                              this.onPlaylistCreated(p);
                            });
                          } else {
                            this.onPlaylistCreated(playlist);
                          }
                        });
                      }}
                      data-toggle="modal"
                      data-target="#ImportMusicServicePlaylistModal"
                    >
                      <FontAwesomeIcon icon={faItunesNote} />
                      &nbsp;Apple Music
                    </button>
                  </li>
                  <li>
                    <button
                      type="button"
                      onClick={() => {
                        NiceModal.show<JSPFPlaylist | JSPFPlaylist[], any>(
                          ImportPlaylistModal
                        ).then((playlist) => {
                          if (Array.isArray(playlist)) {
                            playlist.forEach((p: JSPFPlaylist) => {
                              this.onPlaylistCreated(p);
                            });
                          } else {
                            this.onPlaylistCreated(playlist);
                          }
                        });
                      }}
                      data-toggle="modal"
                      data-target="#ImportPlaylistModal"
                    >
                      <FontAwesomeIcon icon={faFileImport} />
                      &nbsp;Upload JSPF file
                    </button>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>
        <PlaylistsList
          onCopiedPlaylist={this.onCopiedPlaylist}
          playlists={playlists}
          activeSection={playlistType}
          onPlaylistEdited={this.onPlaylistEdited}
          onPlaylistDeleted={this.onPlaylistDeleted}
          view={view}
          page={page}
          handleClickPrevious={handleClickPrevious}
          handleClickNext={handleClickNext}
          pageCount={pageCount}
        >
          {this.isCurrentUserPage() && [
            <Card
              key="new-playlist"
              className={`new-playlist ${
                view === PlaylistView.LIST ? "list-view" : ""
              }`}
              data-toggle="modal"
              data-target="#CreateOrEditPlaylistModal"
              onClick={() => {
                NiceModal.show<JSPFPlaylist, any>(
                  CreateOrEditPlaylistModal
                ).then((playlist) => {
                  this.onPlaylistCreated(playlist);
                });
              }}
            >
              <div>
                <FontAwesomeIcon icon={faPlusCircle as IconProp} size="2x" />
                <span>Create new playlist</span>
              </div>
            </Card>,
          ]}
        </PlaylistsList>
      </div>
    );
  }
}

export function UserPlaylistsWrapper() {
  const data = useLoaderData() as UserPlaylistsLoaderData;
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);
  const type = searchParams.get("type") || "";

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPageNo - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.min(currPageNo + 1, data.pageCount).toString(),
    });
  };

  const playlistType =
    type === "collaborative"
      ? PlaylistType.collaborations
      : PlaylistType.playlists;

  const handleSetPlaylistType = (newType: PlaylistType) => {
    const newParams = { ...searchParamsObj };
    if (newType === PlaylistType.collaborations) {
      newParams.type = "collaborative";
    } else {
      delete newParams?.type;
    }
    setSearchParams(newParams);
  };

  return (
    <UserPlaylists
      {...data}
      page={currPageNo}
      playlistType={playlistType}
      handleClickPrevious={handleClickPrevious}
      handleClickNext={handleClickNext}
      handleSetPlaylistType={handleSetPlaylistType}
    />
  );
}
