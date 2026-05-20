import {
  faListAlt,
  faPlusCircle,
  faUsers,
  faFileImport,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import {
  faSpotify,
  faItunesNote,
  faSoundcloud,
} from "@fortawesome/free-brands-svg-icons";
import * as React from "react";
import { orderBy } from "lodash";
import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLoaderData, useNavigation, useSearchParams } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { useAtom } from "jotai";
import { atomWithStorage } from "jotai/utils";
import Card from "../../components/Card";
import Pill from "../../components/Pill";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import ImportPlaylistModal from "./components/ImportJSPFPlaylistModal";
import ImportSpotifyPlaylistModal from "./components/ImportSpotifyPlaylistModal";
import ImportAppleMusicPlaylistModal from "./components/ImportAppleMusicPlaylistModal";
import ImportSoundCloudPlaylistModal from "./components/ImportSoundCloudPlaylistModal";
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
  searchTerm: string;
};

export enum SortOption {
  RELEVANCE = "relevance",
  DATE_CREATED = "dateCreated",
  DATE_UPDATED = "dateUpdated",
  TITLE = "title",
  CREATOR = "creator",
  RANDOM = "random",
}

type BrowseSortOption =
  | SortOption.DATE_CREATED
  | SortOption.DATE_UPDATED
  | SortOption.TITLE
  | SortOption.CREATOR;

type PlaylistSortCriterion = (playlist: JSPFPlaylist) => string | number;
type PlaylistSortOrder = "asc" | "desc";

function isBrowseSortOption(option: SortOption): option is BrowseSortOption {
  return (
    option === SortOption.DATE_CREATED ||
    option === SortOption.DATE_UPDATED ||
    option === SortOption.TITLE ||
    option === SortOption.CREATOR
  );
}

type UserPlaylistsLoaderData = UserPlaylistsProps;

type UserPlaylistsClassProps = UserPlaylistsProps & {
  page: number;
  playlistType: PlaylistType;
  searchQuery: string;
  urlSort: SortOption;
  isLoading: boolean;
  handleClickPrevious: () => void;
  handleClickNext: () => void;
  handleSetPlaylistType: (newType: PlaylistType) => void;
  onSearchSubmit: (query: string) => void;
  onSortChangeDuringSearch: (sort: SortOption) => void;
  initialView: PlaylistView;
  setPersistentView: (view: PlaylistView) => void;
  initialSort: SortOption;
  setPersistentSort: (sort: SortOption) => void;
};

const playlistViewAtom = atomWithStorage<PlaylistView>(
  "lb_playlists_overview_view",
  PlaylistView.GRID
);
const playlistSortAtom = atomWithStorage<SortOption>(
  "lb_playlists_overview_sort",
  SortOption.DATE_CREATED
);
const playlistTypeAtom = atomWithStorage<string>(
  "lb_playlists_overview_type",
  ""
);
export const MIN_SEARCH_LENGTH = 3;

export default class UserPlaylists extends React.Component<
  UserPlaylistsClassProps,
  UserPlaylistsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserPlaylistsClassProps) {
    super(props);
    const { playlists, initialView, initialSort, searchQuery, urlSort } = props;
    const isSearchActive = searchQuery.length >= MIN_SEARCH_LENGTH;
    this.state = {
      playlists: playlists?.map((pl) => pl.playlist) ?? [],
      sortBy: isSearchActive ? urlSort : initialSort,
      view: initialView,
      searchTerm: searchQuery,
    };
  }

  componentDidUpdate(prevProps: Readonly<UserPlaylistsClassProps>): void {
    const {
      playlists,
      initialView,
      initialSort,
      playlistType,
      searchQuery,
      urlSort,
    } = this.props;
    const { sortBy } = this.state;

    if (prevProps.playlistType !== playlistType) {
      this.setState(
        {
          playlists: playlists.map((pl) => pl.playlist),
          sortBy: initialSort,
          view: initialView,
          searchTerm: "",
        },
        () => {
          this.applyBrowseSort(initialSort);
        }
      );
      return;
    }

    if (prevProps.searchQuery !== searchQuery) {
      const isSearchActive = this.isSearchActive();
      this.setState(
        {
          searchTerm: searchQuery,
          sortBy: isSearchActive ? urlSort : initialSort,
        },
        () => {
          if (!isSearchActive) {
            this.applyBrowseSort(initialSort);
          }
        }
      );
    }

    if (prevProps.urlSort !== urlSort && this.isSearchActive()) {
      this.setState({ sortBy: urlSort });
    }

    if (prevProps.playlists !== playlists) {
      this.setState({ playlists: playlists.map((pl) => pl.playlist) }, () => {
        if (!this.isSearchActive()) {
          this.applyBrowseSort(sortBy || initialSort);
        }
      });
    }

    if (prevProps.initialView !== initialView) {
      this.setState({ view: initialView });
    }

    if (prevProps.initialSort !== initialSort && !this.isSearchActive()) {
      this.setState({ sortBy: initialSort }, () => {
        this.applyBrowseSort(initialSort);
      });
    }
  }

  isSearchActive = () => {
    const { searchQuery } = this.props;
    return searchQuery.length >= MIN_SEARCH_LENGTH;
  };

  getEmptyMessage = (): string | undefined => {
    const { playlistCount, searchQuery, isLoading } = this.props;
    const { playlists } = this.state;

    if (isLoading || playlists.length > 0) {
      return undefined;
    }
    if (this.isSearchActive()) {
      return `No playlists match "${searchQuery}"`;
    }
    if (playlistCount === 0) {
      return "No playlists to show yet. Come back later !";
    }

    return undefined;
  };

  handleSearchTermChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const searchTerm = e.target.value;
    this.setState({ searchTerm });

    if (!searchTerm.trim() && this.isSearchActive()) {
      this.props.onSearchSubmit("");
    }
  };

  handleSearchKeyEsc = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.currentTarget.blur();
    }
  };

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

  applyBrowseSort = (option: SortOption) => {
    const { playlists } = this.state;
    const { setPersistentSort } = this.props;
    setPersistentSort(option);
    if (option === SortOption.RANDOM) {
      this.setState({
        sortBy: option,
        playlists: [...playlists].sort(() => Math.random() - 0.5),
      });
      return;
    }

    if (option === SortOption.RELEVANCE) {
      return;
    }

    if (!isBrowseSortOption(option)) {
      return;
    }

    const sortPlaylists = (
      criteria: PlaylistSortCriterion[],
      sortOrders: PlaylistSortOrder[]
    ): JSPFPlaylist[] => orderBy([...playlists], criteria, sortOrders);

    const criterias: Record<BrowseSortOption, PlaylistSortCriterion> = {
      [SortOption.DATE_CREATED]: (pl) => new Date(pl.date).getTime(),
      [SortOption.TITLE]: (pl) => pl.title.toLowerCase(),
      [SortOption.CREATOR]: (pl) => pl.creator.toLowerCase(),
      [SortOption.DATE_UPDATED]: (pl) =>
        getPlaylistExtension(pl)?.last_modified_at || pl.date,
    };

    const orders: Record<BrowseSortOption, PlaylistSortOrder> = {
      [SortOption.DATE_CREATED]: "desc",
      [SortOption.TITLE]: "asc",
      [SortOption.CREATOR]: "asc",
      [SortOption.DATE_UPDATED]: "desc",
    };

    const sortingCriteriaBasedOnOption: PlaylistSortCriterion[] = [
      criterias[option],
      ...Object.values(criterias).filter((c) => c !== criterias[option]),
    ];

    const sortingOrdersBasedOnOption: PlaylistSortOrder[] = [
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

  setSortOption = (option: SortOption) => {
    const { onSortChangeDuringSearch } = this.props;
    if (this.isSearchActive()) {
      onSortChangeDuringSearch(option);
      this.setState({ sortBy: option });
      return;
    }
    this.applyBrowseSort(option);
  };

  handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const { onSearchSubmit } = this.props;
    const { searchTerm } = this.state;
    onSearchSubmit(searchTerm.trim());
  };

  renderSortOptions = () => {
    const isSearchActive = this.isSearchActive();
    const options = [
      ...(isSearchActive
        ? [{ value: SortOption.RELEVANCE, label: "Best match" }]
        : []),
      { value: SortOption.DATE_CREATED, label: "Date Created" },
      { value: SortOption.DATE_UPDATED, label: "Date Updated" },
      { value: SortOption.TITLE, label: "Title" },
      { value: SortOption.CREATOR, label: "Creator" },
      ...(!isSearchActive
        ? [{ value: SortOption.RANDOM, label: "Random" }]
        : []),
    ];

    return options.map((option) => (
      <option key={option.value} value={option.value}>
        {option.label}
      </option>
    ));
  };

  render() {
    const {
      user,
      pageCount,
      page,
      playlistType,
      handleClickPrevious,
      handleClickNext,
      setPersistentView,
    } = this.props;
    const { playlists, sortBy, view, searchTerm } = this.state;
    const { currentUser } = this.context;

    return (
      <div role="main" id="playlists-page">
        <Helmet>
          <title>{`${
            user?.name === currentUser?.name ? "Your" : `${user?.name}'s`
          } Playlists`}</title>
        </Helmet>
        <div className="tertiary-nav">
          <div className="playlist-view-options flex-wrap">
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
                onClick={() => {
                  this.setState({ view: PlaylistView.GRID });
                  setPersistentView(PlaylistView.GRID);
                }}
                title="Grid view"
              >
                <FontAwesomeIcon icon={faGrid} fixedWidth />
              </Pill>
              <Pill
                active={view === PlaylistView.LIST}
                type="secondary"
                onClick={() => {
                  this.setState({ view: PlaylistView.LIST });
                  setPersistentView(PlaylistView.LIST); // Atom/Storage..
                }}
                title="List view"
              >
                <FontAwesomeIcon icon={faStacked} fixedWidth />
              </Pill>
            </div>
          </div>
          <div className="playlist-view-options flex-wrap">
            <div className="playlist-sort-controls">
              <label htmlFor="sort-by">Sort by:</label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) =>
                  this.setSortOption(e.target.value as SortOption)
                }
                className="form-select"
                style={{ width: "200px" }}
              >
                {this.renderSortOptions()}
              </select>
            </div>

            <div className="playlist-search-controls">
              <form className="search-bar" onSubmit={this.handleSearchSubmit}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Search playlists"
                  value={searchTerm}
                  onChange={this.handleSearchTermChange}
                  onKeyDown={this.handleSearchKeyEsc}
                />
                <button type="submit" disabled={this.props.isLoading}>
                  <FontAwesomeIcon icon={faMagnifyingGlass as IconProp} />
                </button>
              </form>
            </div>

            {this.isCurrentUserPage() && (
              <div
                className="d-flex align-items-center"
                style={{ gap: "10px" }}
              >
                <button
                  className="btn btn-info"
                  type="button"
                  style={{ borderRadius: "5px" }}
                  onClick={() => {
                    NiceModal.show<JSPFPlaylist, any>(
                      CreateOrEditPlaylistModal
                    ).then((playlist) => {
                      this.onPlaylistCreated(playlist);
                    });
                  }}
                >
                  <FontAwesomeIcon icon={faPlusCircle} />
                  &nbsp;Create Playlist
                </button>
                <div className="dropdown">
                  <button
                    className="btn btn-info dropdown-toggle"
                    type="button"
                    id="ImportPlaylistDropdown"
                    data-bs-toggle="dropdown"
                    aria-haspopup="true"
                  >
                    <FontAwesomeIcon icon={faPlusCircle} title="Import" />
                    &nbsp;Import&nbsp;
                  </button>
                  <ul
                    className="dropdown-menu dropdown-menu-right"
                    aria-labelledby="ImportPlaylistDropdown"
                  >
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
                      className="dropdown-item"
                    >
                      <FontAwesomeIcon icon={faSpotify} />
                      &nbsp;Spotify
                    </button>
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
                      className="dropdown-item"
                    >
                      <FontAwesomeIcon icon={faItunesNote} />
                      &nbsp;Apple Music
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        NiceModal.show<JSPFPlaylist[], any>(
                          ImportSoundCloudPlaylistModal
                        ).then((newPlaylists) => {
                          newPlaylists.forEach(this.onPlaylistCreated);
                        });
                      }}
                      className="dropdown-item"
                    >
                      <FontAwesomeIcon icon={faSoundcloud} />
                      &nbsp;SoundCloud
                    </button>
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
                      className="dropdown-item"
                    >
                      <FontAwesomeIcon icon={faFileImport} />
                      &nbsp;Upload JSPF file
                    </button>
                  </ul>
                </div>
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
          isLoading={this.props.isLoading}
          emptyMessage={this.getEmptyMessage()}
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

const parseUrlSort = (sortParam: string | null): SortOption => {
  const validSorts = Object.values(SortOption);
  if (sortParam && validSorts.includes(sortParam as SortOption)) {
    return sortParam as SortOption;
  }
  return SortOption.RELEVANCE;
};

export function UserPlaylistsWrapper() {
  const data = useLoaderData() as UserPlaylistsLoaderData;
  const navigation = useNavigation();
  const isLoading = navigation.state === "loading";
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const skipTypeRestoreRef = React.useRef(false);
  const [persistentView, setPersistentView] = useAtom(playlistViewAtom);
  const [persistentSort, setPersistentSort] = useAtom(playlistSortAtom);
  const [persistentType, setPersistentType] = useAtom(playlistTypeAtom);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);
  const type = searchParams.get("type") || persistentType;
  const searchQuery = searchParams.get("search") || "";
  const urlSort = parseUrlSort(searchParams.get("sort"));

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPageNo - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: (currPageNo + 1).toString(),
    });
  };

  const playlistType =
    type === "collaborative"
      ? PlaylistType.collaborations
      : PlaylistType.playlists;

  const handleSetPlaylistType = (newType: PlaylistType) => {
    skipTypeRestoreRef.current = true;
    const newParams: Record<string, string> = { page: "1" };
    if (newType === PlaylistType.collaborations) {
      newParams.type = "collaborative";
      setPersistentType("collaborative");
    } else {
      setPersistentType("");
    }
    setSearchParams(newParams);
  };

  const onSearchSubmit = (query: string) => {
    const newParams: Record<string, string> = {
      ...searchParamsObj,
      page: "1",
    };
    if (!query || query.length < MIN_SEARCH_LENGTH) {
      delete newParams.search;
      delete newParams.sort;
    } else {
      newParams.search = query;
      newParams.sort = SortOption.RELEVANCE;
    }
    setSearchParams(newParams);
  };

  const onSortChangeDuringSearch = (sort: SortOption) => {
    const newParams: Record<string, string> = {
      ...searchParamsObj,
      sort,
      page: "1",
    };
    setSearchParams(newParams);
  };

  React.useEffect(() => {
    if (skipTypeRestoreRef.current) {
      skipTypeRestoreRef.current = false;
      return;
    }
    if (!searchParams.get("type") && persistentType === "collaborative") {
      const newParams: Record<string, string> = {
        page: searchParams.get("page") || "1",
        type: "collaborative",
      };
      setSearchParams(newParams);
    }
  }, [searchParams, persistentType]);

  return (
    <UserPlaylists
      {...data}
      page={currPageNo}
      playlistType={playlistType}
      searchQuery={searchQuery}
      urlSort={urlSort}
      isLoading={isLoading}
      handleClickPrevious={handleClickPrevious}
      handleClickNext={handleClickNext}
      handleSetPlaylistType={handleSetPlaylistType}
      onSearchSubmit={onSearchSubmit}
      onSortChangeDuringSearch={onSortChangeDuringSearch}
      initialView={persistentView}
      setPersistentView={setPersistentView}
      initialSort={persistentSort}
      setPersistentSort={setPersistentSort}
    />
  );
}
