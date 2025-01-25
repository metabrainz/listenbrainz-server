/* eslint-disable jsx-a11y/anchor-is-valid,camelcase,react/jsx-no-bind */

import * as React from "react";

import {
  faLink,
  faQuestionCircle,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";

import NiceModal from "@ebay/nice-modal-react";

import { groupBy, isNil, isNull, isString, pick, size, sortBy } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import ReactTooltip from "react-tooltip";
import Loader from "../../components/Loader";
import ListenCard from "../../common/listens/ListenCard";
import ListenControl from "../../common/listens/ListenControl";
import MBIDMappingModal from "../../common/listens/MBIDMappingModal";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getRecordingMSID } from "../../utils/utils";
import MultiTrackMBIDMappingModal, {
  MatchingTracksResults,
} from "./MultiTrackMBIDMappingModal";
import Accordion from "../../common/Accordion";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import { RouteQuery } from "../../utils/Loader";

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
  const list = [
    {
      artist_name: "home grown",
      listened_at: "2025-01-18T20:43:47.000Z",
      recording_msid: "e2b4433c-94ad-4c7f-aa69-45038fbc875f",
      recording_name: "wayfarer",
      release_name: "wayfarer",
    },
    {
      artist_name: "May-Flowa",
      listened_at: "2025-01-18T20:08:47.000Z",
      recording_msid: "a0570ca2-003d-4b45-b6e4-3cf93091b9cd",
      recording_name: "poolside",
      release_name: "poolside",
    },
    {
      artist_name: "May-Flowa",
      listened_at: "2025-01-18T20:08:47.000Z",
      recording_msid: "a0570ca2-003d-4b45-b6e4-3cf93091b9cd",
      recording_name: "poolside",
      release_name: "poolside",
    },
    {
      artist_name: "Bastido, Donkeychote",
      listened_at: "2025-01-18T19:42:54.000Z",
      recording_msid: "a45ce2c0-a708-4130-8dae-26b1e2703fe0",
      recording_name: "silver linings",
      release_name: "rooftops",
    },
    {
      artist_name: "ikeya",
      listened_at: "2025-01-18T19:40:09.000Z",
      recording_msid: "95762cd4-0cc0-4feb-94b5-e80b25b47c61",
      recording_name: "chasing the sun",
      release_name: "chasing the sun",
    },
  ];
  const [deletedListens, setDeletedListens] = React.useState<Array<string>>([]);
  const [unlinkedListens, setUnlinkedListens] = React.useState<
    Array<UnlinkedListens>
  >(list);
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
      // Remove successfully matched items from the page
      setUnlinkedListens((prevValue) =>
        prevValue.filter((md) => !matchedTracks[md.recording_msid])
      );
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
        possible, which provides rich data like tags, album, artists, cover art,
        and more.
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
        <a href="https://musicbrainz.org/">MusicBrainz</a> is the open-source
        music encyclopedia that ListenBrainz uses to display information about
        your music.&nbsp;
        <a href="https://wiki.musicbrainz.org/How_to_Contribute">
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
                          // Remove successfully matched item from the page
                          setUnlinkedListens((prevValue) =>
                            prevValue.filter(
                              (md) =>
                                md.recording_msid !==
                                listen.track_metadata.additional_info
                                  ?.recording_msid
                            )
                          );
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
        <ul className="pager" style={{ display: "flex" }}>
          <li className={`previous ${currPage <= 1 ? "disabled" : ""}`}>
            <Link
              to={`?page=${Math.max(currPage - 1, 1)}`}
              role="button"
              aria-disabled={currPage >= totalPages}
            >
              &larr; Previous
            </Link>
          </li>
          <li
            className={`next ${currPage >= totalPages ? "disabled" : ""}`}
            style={{ marginLeft: "auto" }}
          >
            <Link
              to={`?page=${Math.min(currPage + 1, totalPages)}`}
              role="button"
              aria-disabled={currPage >= totalPages}
            >
              Next &rarr;
            </Link>
          </li>
        </ul>
      </div>
    </>
  );
}
