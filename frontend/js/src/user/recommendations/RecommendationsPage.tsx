/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";

import { faInfoCircle, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { isUndefined, set } from "lodash";
import { Link, useLoaderData } from "react-router-dom";
import { ReactSortable } from "react-sortablejs";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import NiceModal from "@ebay/nice-modal-react";
import PlaylistItemCard from "../../playlists/components/PlaylistItemCard";
import {
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
} from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { preciseTimestamp } from "../../utils/utils";
import RecommendationPlaylistSettings from "./components/RecommendationPlaylistSettings";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import HorizontalScrollContainer from "../../components/HorizontalScrollContainer";
import StatsExplanationsModal from "../../common/stats/StatsExplanationsModal";

export type RecommendationsPageProps = {
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
};

type RecommendationsPageLoaderData = RecommendationsPageProps;

export type RecommendationsPageState = {
  playlists: JSPFPlaylist[];
  selectedPlaylist?: JSPFPlaylist;
};

function getPlaylistInfo(
  playlist: JSPFPlaylist,
  isOld = false
): { shortTitle: string; cssClasses: string } {
  const extension = getPlaylistExtension(playlist);
  const sourcePatch =
    extension?.additional_metadata?.algorithm_metadata?.source_patch;
  let year;
  switch (sourcePatch) {
    case "weekly-jams":
      return {
        shortTitle: !isOld ? "Weekly Jams" : `Last Week's Jams`,
        cssClasses: "weekly-jams green",
      };
    case "weekly-exploration":
      return {
        shortTitle: !isOld ? "Weekly Exploration" : `Last Week's Exploration`,
        cssClasses: "green",
      };
    case "daily-jams":
      return {
        shortTitle: "Daily Jams",
        cssClasses: "blue",
      };
    case "top-discoveries-for-year":
      // get year from title, fallback to using creation date minus 1
      year =
        playlist.title.match(/\d{2,4}/)?.[0] ??
        new Date(playlist.date).getUTCFullYear() - 1;
      return {
        shortTitle: `${year} Top Discoveries`,
        cssClasses: "red",
      };
    case "top-missed-recordings-for-year":
      // get year from title, fallback to using creation date minus 1
      year =
        playlist.title.match(/\d{2,4}/)?.[0] ??
        new Date(playlist.date).getUTCFullYear() - 1;
      return {
        shortTitle: `${year} Missed Tracks`,
        cssClasses: "red",
      };
    default:
      return {
        shortTitle: playlist.title,
        cssClasses: "blue",
      };
  }
}

export default function RecommendationsPage() {
  // Context
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  // Loader
  const props = useLoaderData() as RecommendationsPageLoaderData;
  const { playlists: loaderPlaylists = [], user } = props;

  // State
  const [playlists, setPlaylists] = React.useState<JSPFPlaylist[]>([]);
  const [selectedPlaylist, setSelectedPlaylist] = React.useState<
    JSPFPlaylist
  >();

  // Functions
  const fetchPlaylist = React.useCallback(
    async (playlistId: string, reloadOnError = false) => {
      try {
        const response = await APIService.getPlaylist(
          playlistId,
          currentUser?.auth_token
        );
        const JSPFObject: JSPFObject = await response.json();

        // React-SortableJS expects an 'id' attribute (non-negociable), so add it to each object
        JSPFObject.playlist?.track?.forEach((jspfTrack: JSPFTrack) => {
          set(jspfTrack, "id", getRecordingMBIDFromJSPFTrack(jspfTrack));
        });
        setSelectedPlaylist(JSPFObject.playlist);
      } catch (error) {
        toast.error(error.message);
        if (reloadOnError) {
          window.location.reload();
        }
      }
    },
    [APIService, currentUser?.auth_token]
  );

  // The playlist prop only contains generic info, not the actual tracks
  // We need to fetch the playlist to get it in full.
  const selectPlaylist: React.ReactEventHandler<HTMLElement> = async (
    event
  ) => {
    if (!(event?.currentTarget instanceof HTMLElement)) {
      return;
    }
    if (
      event.currentTarget.closest(".dragscroll")?.classList.contains("dragging")
    ) {
      // We are dragging with the dragscroll library, ignore the click
      event.preventDefault();
      return;
    }
    const { playlistId } = event.currentTarget.dataset;
    if (!playlistId) {
      toast.error("No playlist to select");
      return;
    }
    await fetchPlaylist(playlistId, true);
  };

  const copyPlaylist: React.ReactEventHandler<HTMLElement> = async (event) => {
    if (!(event?.currentTarget instanceof HTMLElement)) {
      return;
    }
    event?.stopPropagation();
    if (
      event.currentTarget.closest(".dragscroll")?.classList.contains("dragging")
    ) {
      // We are dragging with the dragscroll library, ignore the click
      event.preventDefault();
      return;
    }
    const playlistId = event.currentTarget?.parentElement?.dataset?.playlistId;

    if (!currentUser?.auth_token) {
      toast.warning("You must be logged in to save playlists");
      return;
    }
    if (!playlistId) {
      toast.error("No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await APIService.copyPlaylist(
        currentUser.auth_token,
        playlistId
      );

      toast.success(
        <>
          Duplicated to playlist&ensp;
          <Link to={`/playlist/${newPlaylistId}/`}>{newPlaylistId}</Link>
        </>
      );
    } catch (error) {
      toast.error(error.message ?? error);
    }
  };

  const hasRightToEdit = (): boolean => {
    return currentUser?.name === user.name;
  };

  const movePlaylistItem = async (evt: any) => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to modify this playlist");
      return;
    }
    if (!hasRightToEdit()) {
      toast.error("You are not authorized to modify this playlist");
      return;
    }
    try {
      await APIService.movePlaylistItem(
        currentUser.auth_token,
        getPlaylistId(selectedPlaylist),
        evt.item.getAttribute("data-recording-mbid"),
        evt.oldIndex,
        evt.newIndex,
        1
      );
    } catch (error) {
      toast.error(error.toString());
      // Revert the move in state.playlist order
      const newTracks = isUndefined(selectedPlaylist)
        ? []
        : [...selectedPlaylist.track];
      // The ol' switcheroo !
      const toMoveBack = newTracks[evt.newIndex];
      newTracks[evt.newIndex] = newTracks[evt.oldIndex];
      newTracks[evt.oldIndex] = toMoveBack;

      setSelectedPlaylist((prevState) => ({
        ...prevState!,
        track: newTracks,
      }));
    }
  };

  const getPlaylistCard = (
    playlist: JSPFPlaylist,
    info: {
      shortTitle: string;
      cssClasses: string;
    }
  ) => {
    const { shortTitle, cssClasses } = info;
    const isLoggedIn = Boolean(currentUser?.auth_token);
    const isCurrentUser = user.name === currentUser?.name;
    const playlistId = getPlaylistId(playlist);
    const extension = getPlaylistExtension(playlist);
    const expiryDate = extension?.additional_metadata?.expires_at;
    let percentElapsed;
    if (expiryDate) {
      const start = new Date(playlist.date).getTime();
      const end = new Date(expiryDate).getTime();
      const today = new Date().getTime();

      const elapsed = Math.abs(today - start);
      const total = Math.abs(end - start);
      percentElapsed = Math.round((elapsed / total) * 100);
    }
    return (
      <div
        key={playlist.identifier}
        className={`${
          selectedPlaylist?.identifier === playlist.identifier ? "selected" : ""
        } ${cssClasses}`}
        onClick={selectPlaylist}
        onKeyDown={(event) => {
          if (["Enter", " "].includes(event.key)) selectPlaylist(event);
        }}
        data-playlist-id={playlistId}
        role="button"
        tabIndex={0}
      >
        {!isUndefined(percentElapsed) && (
          <div
            className={`playlist-timer ${
              percentElapsed > 75 ? "pressing" : ""
            }`}
            title={`Deleted in ${preciseTimestamp(expiryDate!, "timeAgo")}`}
            style={{
              ["--degrees-progress" as any]: `${
                (percentElapsed / 100) * 360
              }deg`,
            }}
          />
        )}
        <div className="title">{shortTitle ?? playlist.title}</div>
        {isLoggedIn && (
          <button
            type="button"
            className="btn btn-info btn-rounded btn-sm"
            onClick={copyPlaylist}
          >
            <FontAwesomeIcon icon={faSave} title="Save to my playlists" />
            <span className="button-text">
              {" "}
              {isCurrentUser ? "Save" : "Duplicate"}
            </span>
          </button>
        )}
      </div>
    );
  };

  // Effect
  React.useEffect(() => {
    const playlistsMapped = loaderPlaylists?.map((pl) => pl.playlist);
    setPlaylists(playlistsMapped);

    if (playlistsMapped.length > 0) {
      const selectPlaylistFromProps =
        playlistsMapped.find((pl) => {
          const extension = getPlaylistExtension(pl);
          const sourcePatch =
            extension?.additional_metadata?.algorithm_metadata?.source_patch;
          return sourcePatch === "weekly-jams";
        }) ?? playlistsMapped[0];
      if (selectPlaylistFromProps) {
        const playlistId = getPlaylistId(selectPlaylistFromProps);
        fetchPlaylist(playlistId);
      }
    }
  }, [fetchPlaylist, loaderPlaylists]);

  React.useEffect(() => {
    if (selectedPlaylist) {
      const listensFromJSPFTracks = selectedPlaylist?.track ?? [];
      dispatch({
        type: "SET_AMBIENT_QUEUE",
        data: listensFromJSPFTracks,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlaylist]);

  return (
    <div id="recommendations" role="main">
      <Helmet>
        <title>{`Created for ${
          user?.name === currentUser?.name ? "you" : `${user?.name}`
        }`}</title>
      </Helmet>
      <h3>Created for {user.name}</h3>

      {!playlists.length ? (
        <div className="text-center">
          <img
            src="/static/img/recommendations/no-freshness.png"
            alt="No recommendations to show"
            style={{ maxHeight: "500px" }}
          />
          <p className="hidden">
            Oh no. Either something’s gone wrong, or you need to submit more
            listens before we can prepare delicious fresh produce just for you.
          </p>
          <div>
            <button
              type="button"
              className="btn btn-link"
              data-toggle="modal"
              data-target="#StatsExplanationsModal"
              onClick={() => {
                NiceModal.show(StatsExplanationsModal);
              }}
            >
              <FontAwesomeIcon icon={faInfoCircle} />
              &nbsp; How and when are recommendations calculated?
            </button>
          </div>
        </div>
      ) : (
        <HorizontalScrollContainer
          className="playlists-masonry"
          showScrollbar={false}
        >
          {playlists.map((playlist, index) => {
            const extension = getPlaylistExtension(playlist);
            const sourcePatch =
              extension?.additional_metadata?.algorithm_metadata?.source_patch;
            const isFirstOfType =
              playlists.findIndex((pl) => {
                const extension2 = getPlaylistExtension(pl);
                const sourcePatch2 =
                  extension2?.additional_metadata?.algorithm_metadata
                    ?.source_patch;
                return sourcePatch === sourcePatch2;
              }) === index;

            const info = getPlaylistInfo(playlist, !isFirstOfType);
            return getPlaylistCard(playlist, info);
          })}
        </HorizontalScrollContainer>
      )}
      {selectedPlaylist && (
        <section id="selected-playlist">
          <div className="playlist-items">
            {selectedPlaylist.track.length > 0 ? (
              <ReactSortable
                handle=".drag-handle"
                list={selectedPlaylist.track as (JSPFTrack & { id: string })[]}
                onEnd={movePlaylistItem}
                setList={(newState) =>
                  setSelectedPlaylist((prevState) => ({
                    ...prevState!,
                    track: newState,
                  }))
                }
              >
                {selectedPlaylist.track.map((track: JSPFTrack, index) => {
                  return (
                    <PlaylistItemCard
                      key={`${track.id}-${index.toString()}`}
                      canEdit={hasRightToEdit()}
                      track={track}
                      showTimestamp={false}
                      showUsername={false}
                      // removeTrackFromPlaylist={this.deletePlaylistItem}
                    />
                  );
                })}
              </ReactSortable>
            ) : (
              <div className="lead text-center">
                <p>Nothing in this playlist yet</p>
              </div>
            )}
          </div>
          <RecommendationPlaylistSettings playlist={selectedPlaylist} />
        </section>
      )}
    </div>
  );
}
