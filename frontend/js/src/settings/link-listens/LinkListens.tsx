/* eslint-disable jsx-a11y/anchor-is-valid,camelcase,react/jsx-no-bind */

import * as React from "react";

import {
  faLink,
  faTrashAlt,
  faSearch,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";

import NiceModal from "@ebay/nice-modal-react";

import { groupBy, isNil, isNull, isString, pick, size, sortBy } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import ReactTooltip from "react-tooltip";
import Fuse from "fuse.js";
import Loader from "../../components/Loader";
import ListenCard from "../../common/listens/ListenCard";
import ListenControl from "../../common/listens/ListenControl";
import MBIDMappingModal from "../../common/listens/MBIDMappingModal";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import {
  getObjectForURLSearchParams,
  getRecordingMSID,
} from "../../utils/utils";
import MultiTrackMBIDMappingModal, {
  MatchingTracksResults,
} from "./MultiTrackMBIDMappingModal";
import Accordion from "../../common/Accordion";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import { RouteQuery } from "../../utils/Loader";
import Pagination from "../../common/Pagination";

export type LinkListensProps = {
  unlinkedListens?: Array<UnlinkedListens>;
  user: ListenBrainzUser;
};

type LinkListensLoaderData = {
  unlinked_listens?: Array<UnlinkedListens>;
  last_updated?: string | null;
};

export interface LinkListensState {
  unlinkedListens: Array<UnlinkedListens>;
  groupedUnlinkedListens: Array<UnlinkedListens[]>;
  deletedListens: Array<string>; // array of recording_msid of deleted items
  currPage: number;
  loading: boolean;
}

export function unlinkedListenDataToListen(
  data: UnlinkedListens,
  user: ListenBrainzUser
): Listen {
  return {
    listened_at: new Date(data.listened_at).getTime() / 1000,
    user_name: user.name,
    track_metadata: {
      artist_name: data.artist_name,
      track_name: data.recording_name,
      release_name: data?.release_name ?? undefined,
      additional_info: {
        recording_msid: data.recording_msid,
      },
    },
  };
}

const EXPECTED_ITEMS_PER_PAGE = 25;

export default function LinkListensPage() {
  // Context
  const { APIService, currentUser: user } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();
  const location = useLocation();
  // Loader
  const { data: loaderData, isLoading } = useQuery<LinkListensLoaderData>(
    RouteQuery(["link-listens"], location.pathname)
  );
  const {
    unlinked_listens: unlinkedListensProps = [],
    last_updated: lastUpdated,
  } = loaderData || {};

  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const pageSearchParam = searchParams.get("page");

  const lastUpdatedHumanReadable = isString(lastUpdated)
    ? new Date(lastUpdated).toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    : "—";
  // State
  const [deletedListens, setDeletedListens] = React.useState<Array<string>>([]);
  const [originalUnlinkedListens, setOriginalUnlinkedListens] = React.useState<
    Array<UnlinkedListens>
  >(unlinkedListensProps);
  const [unlinkedListens, setUnlinkedListens] = React.useState<
    Array<UnlinkedListens>
  >(unlinkedListensProps);
  const [filterType, setFilterType] = React.useState("album"); // Default filter type
  const [searchQuery, setSearchQuery] = React.useState(""); // To store the search input
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const searchOptions = {
      threshold: 0.3,
    };
    let key;
    switch (filterType) {
      case "artist":
        key = "artist_name";
        break;
      case "track":
        key = "recording_name";
        break;
      case "album":
      default:
        key = "release_name";
        break;
    }
    const fuzzysearch = new Fuse(originalUnlinkedListens, {
      keys: [key],
      ...searchOptions,
    });
    const trimmedSearchQuery = searchQuery.trim();
    if (filterType === "artist") {
      const filtered = fuzzysearch
        .search(trimmedSearchQuery)
        .map((result) => result.item);
      setUnlinkedListens(filtered);
    } else {
      const albumsByArtist = fuzzysearch
        .search(trimmedSearchQuery)
        .map((result) => result.item.release_name);
      const filtered = originalUnlinkedListens.filter((listen) =>
        albumsByArtist.includes(listen.release_name)
      );
      setUnlinkedListens(filtered);
    }
    setSearchParams({ page: "1" }, { preventScrollReset: true });
  };
  const handleReset = () => {
    setSearchQuery("");
    setUnlinkedListens(originalUnlinkedListens);
    setSearchParams({ page: "1" }, { preventScrollReset: true });
  };
  const unsortedGroupedUnlinkedListens = groupBy(
    unlinkedListens,
    "release_name"
  );
  // remove and store a catchall group with no release name
  const noReleaseNameGroup = pick(unsortedGroupedUnlinkedListens, "null");
  if (size(noReleaseNameGroup) > 0) {
    // remove catchall group from other groups,
    // we want to add it at the very end
    delete unsortedGroupedUnlinkedListens.null;
  }
  const sortedUnlinkedListensGroups = sortBy(
    unsortedGroupedUnlinkedListens,
    "length"
  ).reverse();
  if (noReleaseNameGroup.null?.length) {
    // re-add the group with no release name at the end,
    // will be displayed as single listens rather than a group
    sortedUnlinkedListensGroups.push(noReleaseNameGroup.null);
  }

  // Pagination
  const currPage = isNull(pageSearchParam) ? 1 : parseInt(pageSearchParam, 10);
  const totalPages = unsortedGroupedUnlinkedListens
    ? Math.ceil(size(unsortedGroupedUnlinkedListens) / EXPECTED_ITEMS_PER_PAGE)
    : 0;

  const offset = (currPage - 1) * EXPECTED_ITEMS_PER_PAGE;
  const itemsOnThisPage = sortedUnlinkedListensGroups.slice(
    offset,
    offset + EXPECTED_ITEMS_PER_PAGE
  );

  // Functions

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPage - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.min(currPage + 1, totalPages).toString(),
    });
  };

  const deleteListen = async (data: UnlinkedListens) => {
    if (user?.auth_token) {
      const listenedAt = new Date(data.listened_at).getTime() / 1000;
      try {
        const status = await APIService.deleteListen(
          user.auth_token,
          data.recording_msid,
          listenedAt
        );
        if (status === 200) {
          setDeletedListens((prevState) =>
            prevState.concat(data.recording_msid)
          );
          toast.info(
            <ToastMsg
              title="Success"
              message={
                "This listen has not been deleted yet, but is scheduled for deletion," +
                " which usually happens shortly after the hour."
              }
            />,
            { toastId: "deleted-track" }
          );
          // Remove the listen from the BrainzPlayer queue
          dispatch({
            type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
            data: {
              track: unlinkedListenDataToListen(data, user),
              index: -1,
            },
          });
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error while deleting listen"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "deleted-track-error" }
        );
      }
    }
  };

  const openMultiTrackMappingModal = React.useCallback(
    async (group: UnlinkedListens[], releaseName: string | null) => {
      const matchedTracks: MatchingTracksResults = await NiceModal.show(
        MultiTrackMBIDMappingModal,
        {
          unlinkedListens: group,
          releaseName,
        }
      );
      // Remove successfully matched items from both states
      const filterOutMatched = (prevValue: Array<UnlinkedListens>) =>
        prevValue.filter((md) => !matchedTracks[md.recording_msid]);
      setUnlinkedListens(filterOutMatched);
      setOriginalUnlinkedListens(filterOutMatched);
      Object.entries(matchedTracks).forEach(([recordingMsid, track]) => {
        // For deleting items from the BrainzPlayer queue, we need to use
        // the metadata it was created from rather than the matched track metadata
        const itemBeforeMatching = group.find(
          ({ recording_msid }) => recordingMsid === recording_msid
        );
        if (itemBeforeMatching) {
          // Remove the listen from the BrainzPlayer queue
          dispatch({
            type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
            data: {
              track: unlinkedListenDataToListen(itemBeforeMatching, user),
              index: -1,
            },
          });
        }
      });
    },
    [dispatch, user]
  );

  // Effects
  React.useEffect(() => {
    // Set the ?page search param in URL on startup if not set, as well as
    // constrain pagination to existing pages, forcing navigation to first page if needed
    if (!pageSearchParam || currPage > totalPages) {
      setSearchParams(
        { page: "1" },
        { preventScrollReset: true, replace: true }
      );
    }
    // Only run once on startup
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // BrainzPlayer
  React.useEffect(() => {
    const unlinkedDataAsListen = itemsOnThisPage.flatMap((x) => [
      ...x.map((y) => unlinkedListenDataToListen(y, user)),
    ]);
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: unlinkedDataAsListen,
    });
  }, [dispatch, itemsOnThisPage, user]);

  return (
    <>
      <Helmet>
        <title>Link with MusicBrainz</title>
      </Helmet>
      <h2 className="page-title">Link with MusicBrainz</h2>
      <ReactTooltip id="matching-tooltip" multiline>
        We automatically match listens with MusicBrainz recordings when
        possible,
        <br />
        which provides rich data like tags, album, artists, cover art, and more.
        <br />
        When a track can&apos;t be auto-matched you can manually link them on
        this page.
        <br />
        Recordings may not exist in MusicBrainz, and need to be added there
        first.
      </ReactTooltip>
      <p>
        Your top 1,000 listens (grouped by album) that have&nbsp;
        <u
          className="link-listens-tooltip"
          data-tip
          data-for="matching-tooltip"
        >
          not been automatically linked
        </u>
        &nbsp;to a MusicBrainz recording.
      </p>
      <p className="small">
        <a
          href="https://musicbrainz.org/"
          target="_blank"
          rel="noopener noreferrer"
        >
          MusicBrainz
        </a>
        &nbsp; is the open-source music encyclopedia that ListenBrainz uses to
        display information about your music.&nbsp;
        <a
          href="https://wiki.musicbrainz.org/How_to_Contribute"
          target="_blank"
          rel="noopener noreferrer"
        >
          Submit missing data to MusicBrainz
        </a>
        .
      </p>
      {!isNil(lastUpdated) && (
        <p className="small">
          Updates every Monday at 2AM (UTC). Last updated{" "}
          {lastUpdatedHumanReadable}
        </p>
      )}
      {unlinkedListensProps.length > 0 && (
        <form
          className="input-group input-group-flex"
          style={{ maxWidth: "400px" }}
          onSubmit={handleSearch}
        >
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="btn btn-info"
          >
            <option value="album">Album</option>
            <option value="artist">Artist</option>
            <option value="track">Track</option>
          </select>
          <div className="input-group-btn">
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-control"
            />
            <button
              type="submit"
              className="btn btn-info"
              disabled={!searchQuery.trim()}
              aria-disabled={!searchQuery.trim()}
              title="Search"
            >
              <FontAwesomeIcon icon={faSearch} />
            </button>
            <button
              type="button"
              className="btn btn-info"
              onClick={handleReset}
              title="Reset"
            >
              Reset
            </button>
          </div>
        </form>
      )}
      <br />
      <div>
        <div id="link-listens">
          <div
            style={{
              height: 0,
              position: "sticky",
              top: "50%",
              zIndex: 1,
            }}
          >
            <Loader isLoading={isLoading} />
          </div>
          {unlinkedListens.length === 0 && (
            <p>
              <strong>No unlinked listens found.</strong>
            </p>
          )}
          {itemsOnThisPage.map((group) => {
            const releaseName = group.at(0)?.release_name ?? null;
            const multiTrackMappingButton = (
              <button
                className="btn btn-link btn-icon color-orange"
                style={{ padding: "0", height: "initial" }}
                type="button"
                onClick={() => {
                  openMultiTrackMappingModal(group, releaseName);
                }}
                data-toggle="modal"
                data-target="#MultiTrackMBIDMappingModal"
              >
                <FontAwesomeIcon icon={faLink} />
              </button>
            );
            const listenCards = group.map((groupItem) => {
              if (
                deletedListens.find(
                  (deletedMSID) => deletedMSID === groupItem.recording_msid
                )
              ) {
                // If the item was deleted, don't show it to the user
                return undefined;
              }
              let additionalActions;
              const listen = unlinkedListenDataToListen(groupItem, user);
              const additionalMenuItems = [];
              if (user?.auth_token) {
                const recordingMSID = getRecordingMSID(listen);
                const canDelete =
                  Boolean(listen.listened_at) && Boolean(recordingMSID);

                if (canDelete) {
                  additionalMenuItems.push(
                    <ListenControl
                      text="Delete Listen"
                      icon={faTrashAlt}
                      action={() => {
                        deleteListen(groupItem);
                      }}
                    />
                  );
                }

                if (listen?.track_metadata?.additional_info?.recording_msid) {
                  const linkWithMB = (
                    <ListenControl
                      buttonClassName="btn btn-link color-orange"
                      text=""
                      title="Link with MusicBrainz"
                      icon={faLink}
                      action={() => {
                        NiceModal.show<TrackMetadata, any>(MBIDMappingModal, {
                          listenToMap: listen,
                        }).then(({ recording_msid }) => {
                          // Remove the listen from the BrainzPlayer queue
                          dispatch({
                            type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
                            data: {
                              track: listen,
                              index: -1,
                            },
                          });
                          const filterOutMatched = (
                            prevValue: Array<UnlinkedListens>
                          ) =>
                            prevValue.filter(
                              (md) =>
                                md.recording_msid !==
                                listen.track_metadata.additional_info
                                  ?.recording_msid
                            );
                          setUnlinkedListens(filterOutMatched);
                          setOriginalUnlinkedListens(filterOutMatched);
                        });
                      }}
                    />
                  );
                  additionalActions = linkWithMB;
                }
              }
              return (
                <ListenCard
                  key={`${groupItem.recording_name}-${groupItem.artist_name}-${groupItem.listened_at}`}
                  showTimestamp
                  showUsername={false}
                  // eslint-disable-next-line react/jsx-no-useless-fragment
                  customThumbnail={<></>}
                  // eslint-disable-next-line react/jsx-no-useless-fragment
                  feedbackComponent={<></>}
                  listen={listen}
                  additionalMenuItems={additionalMenuItems}
                  additionalActions={additionalActions}
                />
              );
            });
            if (!releaseName?.length) {
              // If this is the group with no release name, return listencards
              // directly instead of an accordion group
              return <div key="no-release-name">{listenCards}</div>;
            }
            return (
              <Accordion
                key={releaseName}
                title={
                  <>
                    {releaseName} <small>({group.length} tracks)</small>
                  </>
                }
                actions={multiTrackMappingButton}
                defaultOpen={group.length === 1}
              >
                {listenCards}
              </Accordion>
            );
          })}
        </div>
        <Pagination
          currentPageNo={currPage}
          totalPageCount={totalPages}
          handleClickPrevious={handleClickPrevious}
          handleClickNext={handleClickNext}
        />
      </div>
    </>
  );
}
