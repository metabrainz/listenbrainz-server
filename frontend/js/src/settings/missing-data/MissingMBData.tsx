/* eslint-disable jsx-a11y/anchor-is-valid,camelcase,react/jsx-no-bind */

import * as React from "react";

import { faLink, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";

import NiceModal from "@ebay/nice-modal-react";

import Loader from "../../components/Loader";
import ListenCard from "../../common/listens/ListenCard";
import ListenControl from "../../common/listens/ListenControl";
import MBIDMappingModal from "../../common/listens/MBIDMappingModal";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import {
  getArtistName,
  getRecordingMSID,
  getTrackName,
} from "../../utils/utils";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

export type MissingMBDataProps = {
  missingData?: Array<MissingMBData>;
  user: ListenBrainzUser;
};

type MissingMBDataLoaderData = {
  missing_data?: Array<MissingMBData>;
};

export interface MissingMBDataState {
  missingData: Array<MissingMBData>;
  deletedListens: Array<string>; // array of recording_msid of deleted items
  currPage?: number;
  loading: boolean;
}

const EXPECTED_ITEMS_PER_PAGE = 25;

export default function MissingMBDataPage() {
  // Context
  const { APIService, currentUser: user } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  // Loader
  const props = useLoaderData() as MissingMBDataLoaderData;
  const { missing_data: missingDataProps = [] } = props;

  // State
  const [missingData, setMissingData] = React.useState<Array<MissingMBData>>(
    missingDataProps.slice(0, EXPECTED_ITEMS_PER_PAGE) || []
  );
  const [deletedListens, setDeletedListens] = React.useState<Array<string>>([]);
  const [currPage, setCurrPage] = React.useState<number>(1);
  const totalPages = missingDataProps
    ? Math.ceil(missingDataProps.length / EXPECTED_ITEMS_PER_PAGE)
    : 0;
  const [loading, setLoading] = React.useState<boolean>(false);

  // Ref
  const missingMBDataTableRef = React.useRef<HTMLDivElement>(null);

  // Functions
  const afterDisplay = () => {
    if (missingMBDataTableRef?.current) {
      missingMBDataTableRef.current.scrollIntoView({ behavior: "smooth" });
    }
    setLoading(false);
  };

  const submitMissingData = (listen: Listen) => {
    // This function submits data to the MusicBrainz server. We have not used
    // fetch here because the endpoint where the submision is being done
    // replies back with HTML and since we cannot redirect via fetch, we have
    // to resort to such obscure method :D
    const form = document.createElement("form");
    form.method = "post";
    form.action = "https://musicbrainz.org/release/add";
    form.target = "_blank";
    const name = document.createElement("input");
    name.type = "hidden";
    name.name = "name";
    name.value = listen.track_metadata?.release_name || "";
    form.appendChild(name);
    const recording = document.createElement("input");
    recording.type = "hidden";
    recording.name = "mediums.0.track.0.name";
    recording.value = getTrackName(listen);
    form.appendChild(recording);
    const artists = getArtistName(listen).split(",");
    artists.forEach((artist, index) => {
      const artistCredit = document.createElement("input");
      artistCredit.type = "hidden";
      artistCredit.name = `artist_credit.names.${index}.artist.name`;
      artistCredit.value = artist;
      form.appendChild(artistCredit);
      if (index !== artists.length - 1) {
        const joiner = document.createElement("input");
        joiner.type = "hidden";
        joiner.name = `artist_credit.names.${index}.join_phrase`;
        joiner.value = ", ";
        form.appendChild(joiner);
      }
    });
    const editNote = document.createElement("textarea");
    editNote.style.display = "none";
    editNote.name = "edit_note";
    editNote.value = `Imported from ${user.name}'s ListenBrainz Missing MusicBrainz Data Page`;
    form.appendChild(editNote);
    document.body.appendChild(form);
    form.submit();
    form.remove();
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
      const offset = (currPage - 1) * EXPECTED_ITEMS_PER_PAGE;
      const updatedPage = currPage - 1;
      setMissingData(
        missingDataProps.slice(offset - EXPECTED_ITEMS_PER_PAGE, offset) || []
      );
      setCurrPage(updatedPage);
      afterDisplay();
      window.history.pushState(null, "", `?page=${updatedPage}`);
    }
  };

  const handleClickNext = () => {
    if (currPage && currPage < totalPages) {
      setLoading(true);
      const offset = currPage * EXPECTED_ITEMS_PER_PAGE;
      const updatedPage = currPage + 1;
      setMissingData(
        missingDataProps.slice(offset, offset + EXPECTED_ITEMS_PER_PAGE) || []
      );
      setCurrPage(updatedPage);
      afterDisplay();
      window.history.pushState(null, "", `?page=${updatedPage}`);
    }
  };

  const missingMBDataAsListen = missingData.map((data) => {
    return {
      listened_at: new Date(data.listened_at).getTime() / 1000,
      user_name: user.name,
      track_metadata: {
        artist_name: data.artist_name,
        track_name: data.recording_name,
        release_name: data?.release_name,
        additional_info: {
          recording_msid: data.recording_msid,
        },
      },
    };
  });

  // Effects
  React.useEffect(() => {
    window.history.replaceState(null, "", `?page=${currPage}`);
  }, []);

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: missingMBDataAsListen,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missingMBDataAsListen]);

  return (
    <>
      <Helmet>
        <title>Missing MusicBrainz Data of {user?.name}</title>
      </Helmet>
      <h2 className="page-title">Missing MusicBrainz Data of {user?.name}</h2>
      <p>
        <a href="https://musicbrainz.org/">MusicBrainz</a> is the open-source
        music encyclopedia that ListenBrainz uses to display information about
        your music.
        <br />
        <br />
        This page displays your top 200 (by listen count) submitted songs that
        we haven&apos;t been able to automatically link with MusicBrainz
        “recordings”, or that don&apos;t yet exist in MusicBrainz. Please take a
        few minutes to link these recordings below, or to{" "}
        <a href="https://wiki.musicbrainz.org/How_to_Contribute">
          submit new data to MusicBrainz
        </a>
        .
      </p>
      <div className="row" style={{ display: "flex", flexWrap: "wrap" }}>
        <div className="col-xs-12 col-md-8">
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
              {missingData.map((data, index) => {
                if (
                  deletedListens.find(
                    (deletedMSID) => deletedMSID === data.recording_msid
                  )
                ) {
                  // If the item was deleted, don't show it to the user
                  return null;
                }
                let additionalActions;
                const listen = missingMBDataAsListen[index];
                const additionalMenuItems = [];
                if (user?.auth_token) {
                  // Commenting this out for now because currently it leads to new eager users creating
                  // a bunch of standalone recordings, and possible duplicates
                  /* const addToMB = (
                  <ListenControl
                    buttonClassName="btn btn-sm"
                    icon={faPlus}
                    title="Add missing recording"
                    text=""
                    // eslint-disable-next-line react/jsx-no-bind
                    action={this.submitMissingData.bind(this, listen)}
                  />
                ); */

                  const recordingMSID = getRecordingMSID(listen);
                  const canDelete =
                    Boolean(listen.listened_at) && Boolean(recordingMSID);

                  if (canDelete) {
                    additionalMenuItems.push(
                      <ListenControl
                        text="Delete Listen"
                        icon={faTrashAlt}
                        action={() => {
                          deleteListen(data);
                        }}
                      />
                    );
                  }

                  if (listen?.track_metadata?.additional_info?.recording_msid) {
                    const linkWithMB = (
                      <ListenControl
                        buttonClassName="btn btn-sm btn-success"
                        text=""
                        title="Link with MusicBrainz"
                        icon={faLink}
                        action={() => {
                          NiceModal.show(MBIDMappingModal, {
                            listenToMap: listen,
                          });
                        }}
                      />
                    );
                    additionalActions = linkWithMB;
                  }
                }
                return (
                  <ListenCard
                    key={`${data.recording_name}-${data.artist_name}-${data.listened_at}`}
                    showTimestamp
                    showUsername={false}
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    customThumbnail={<></>}
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    listen={missingMBDataAsListen[index]}
                    additionalMenuItems={additionalMenuItems}
                    additionalActions={additionalActions}
                  />
                );
              })}
            </div>
            <ul className="pager" style={{ display: "flex" }}>
              <li
                className={`previous ${
                  currPage && currPage <= 1 ? "hidden" : ""
                }`}
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
        </div>
      </div>
    </>
  );
}
