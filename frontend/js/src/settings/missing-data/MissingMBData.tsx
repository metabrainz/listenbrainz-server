/* eslint-disable jsx-a11y/anchor-is-valid,camelcase,react/jsx-no-bind */

import * as React from "react";

import { faLink, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { useLocation, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";

import NiceModal from "@ebay/nice-modal-react";

import { groupBy, isNil, isNull, pick, size, sortBy } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
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

export type MissingMBDataProps = {
  missingData?: Array<MissingMBData>;
  user: ListenBrainzUser;
};

type MissingMBDataLoaderData = {
  missing_data?: Array<MissingMBData>;
  last_updated?: string | null;
};

export interface MissingMBDataState {
  missingData: Array<MissingMBData>;
  groupedMissingData: Array<MissingMBData[]>;
  deletedListens: Array<string>; // array of recording_msid of deleted items
  currPage: number;
  loading: boolean;
}

export function missingDataToListen(
  data: MissingMBData,
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

export default function MissingMBDataPage() {
  // Context
  const { APIService, currentUser: user } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();
  const location = useLocation();
  // Loader
  const { data: loaderData } = useQuery<MissingMBDataLoaderData>(
    RouteQuery(["missing-data"], location.pathname)
  );
  const { missing_data: missingDataProps = [], last_updated: lastUpdated } =
    loaderData || {};

  const [searchParams, setSearchParams] = useSearchParams();
  const pageSearchParam = searchParams.get("page");

  // State
  const [loading, setLoading] = React.useState<boolean>(false);
  const [deletedListens, setDeletedListens] = React.useState<Array<string>>([]);
  const [missingData, setMissingData] = React.useState<Array<MissingMBData>>(
    missingDataProps
  );
  const unsortedGroupedMissingData = groupBy(missingData, "release_name");
  // remove and store a catchall group with no release name
  const noReleaseNameGroup = pick(unsortedGroupedMissingData, "null");
  if (size(noReleaseNameGroup) > 0) {
    // remove catchall group from other groups,
    // we want to add it at the very end
    delete unsortedGroupedMissingData.null;
  }
  const sortedMissingDataGroups = sortBy(
    unsortedGroupedMissingData,
    "length"
  ).reverse();
  if (noReleaseNameGroup.null?.length) {
    // re-add the group with no release name at the end,
    // will be displayed as single listens rather than a group
    sortedMissingDataGroups.push(noReleaseNameGroup.null);
  }

  // Pagination
  const currPage = isNull(pageSearchParam) ? 1 : parseInt(pageSearchParam, 10);
  const totalPages = unsortedGroupedMissingData
    ? Math.ceil(size(unsortedGroupedMissingData) / EXPECTED_ITEMS_PER_PAGE)
    : 0;

  const offset = (currPage - 1) * EXPECTED_ITEMS_PER_PAGE;
  const itemsOnThisPage = sortedMissingDataGroups.slice(
    offset,
    offset + EXPECTED_ITEMS_PER_PAGE
  );

  // Ref
  const missingMBDataTableRef = React.useRef<HTMLDivElement>(null);

  // Functions
  const afterDisplay = () => {
    if (missingMBDataTableRef?.current) {
      missingMBDataTableRef.current.scrollIntoView({ behavior: "smooth" });
    }
    setLoading(false);
  };

  const deleteListen = async (data: MissingMBData) => {
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
              track: missingDataToListen(data, user),
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

  const handleClickPrevious = () => {
    if (currPage && currPage > 1) {
      setLoading(true);
      const updatedPage = currPage - 1;
      setSearchParams({ page: updatedPage.toString() });
      afterDisplay();
    }
  };

  const handleClickNext = () => {
    if (currPage && currPage < totalPages) {
      setLoading(true);
      const updatedPage = currPage + 1;
      setSearchParams({ page: updatedPage.toString() });
      afterDisplay();
    }
  };

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
    const missingMBDataAsListen = itemsOnThisPage.flatMap((x) => [
      ...x.map((y) => missingDataToListen(y, user)),
    ]);
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: missingMBDataAsListen,
    });
  }, [dispatch, itemsOnThisPage, user]);

  return (
    <>
      <Helmet>
        <title>Missing MusicBrainz Data of {user?.name}</title>
      </Helmet>
      <h2 className="page-title">Missing MusicBrainz Data of {user?.name}</h2>
      <p>
        Your top 1000 listens that haven&apos;t been automatically linked. Link
        the listens below, or&nbsp;
        <a href="https://wiki.musicbrainz.org/How_to_Contribute">
          submit new data to MusicBrainz
        </a>
        .
      </p>
      <p>
        <a href="https://musicbrainz.org/">MusicBrainz</a> is the open-source
        music encyclopedia that ListenBrainz uses to display information about
        your music.
      </p>
      {!isNil(lastUpdated) && (
        <p>Last updated {new Date(lastUpdated).toLocaleDateString()}</p>
      )}
      <br />
      <div>
        <div id="missingMBData" ref={missingMBDataTableRef}>
          <div
            style={{
              height: 0,
              position: "sticky",
              top: "50%",
              zIndex: 1,
            }}
          >
            <Loader isLoading={loading} />
          </div>
          {itemsOnThisPage.map((group) => {
            const releaseName = group.at(0)?.release_name ?? null;
            const multiTrackMappingButton = (
              <button
                className="btn btn-link btn-icon color-orange"
                style={{ padding: "0", height: "initial" }}
                type="button"
                onClick={(e) => {
                  NiceModal.show<MatchingTracksResults, any>(
                    MultiTrackMBIDMappingModal,
                    {
                      missingData: group,
                      releaseName,
                    }
                  ).then((matchedTracks) => {
                    Object.entries(matchedTracks).forEach(
                      ([recordingMsid, track]) => {
                        // For deleting items from the BrainzPlayer queue, we need to use
                        // the metadata it was created from rather than the matched track metadata
                        const itemBeforeMatching = group.find(
                          ({ recording_msid }) =>
                            recordingMsid === recording_msid
                        );
                        if (itemBeforeMatching) {
                          // Remove the listen from the BrainzPlayer queue
                          dispatch({
                            type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
                            data: {
                              track: missingDataToListen(
                                itemBeforeMatching,
                                user
                              ),
                              index: -1,
                            },
                          });
                        }
                      }
                    );
                    // Remove successfully matched items from the page
                    setMissingData((prevValue) =>
                      prevValue.filter(
                        (md) => !matchedTracks[md.recording_msid]
                      )
                    );
                  });
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
              const listen = missingDataToListen(groupItem, user);
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
                          setMissingData((prevValue) =>
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
          <li
            className={`previous ${currPage && currPage <= 1 ? "hidden" : ""}`}
          >
            <a
              role="button"
              onClick={handleClickPrevious}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleClickPrevious();
              }}
              tabIndex={0}
            >
              &larr; Previous
            </a>
          </li>
          <li
            className={`next ${
              currPage && currPage >= totalPages ? "hidden" : ""
            }`}
            style={{ marginLeft: "auto" }}
          >
            <a
              role="button"
              onClick={handleClickNext}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleClickNext();
              }}
              tabIndex={0}
            >
              Next &rarr;
            </a>
          </li>
        </ul>
      </div>
    </>
  );
}
