/* eslint-disable jsx-a11y/anchor-is-valid,camelcase,react/jsx-no-bind */

import * as React from "react";
import { toast } from "react-toastify";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { faLink, faPlus, faTrashAlt } from "@fortawesome/free-solid-svg-icons";

import NiceModal from "@ebay/nice-modal-react";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";

import GlobalAppContext from "../utils/GlobalAppContext";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import {
  getArtistName,
  getPageProps,
  getRecordingMSID,
  getTrackName,
} from "../utils/utils";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import Loader from "../components/Loader";
import { ToastMsg } from "../notifications/Notifications";
import MBIDMappingModal from "../mbid-mapping/MBIDMappingModal";

export type MissingMBDataProps = {
  missingData?: Array<MissingMBData>;
  user: ListenBrainzUser;
};

export interface MissingMBDataState {
  missingData: Array<MissingMBData>;
  deletedListens: Array<string>; // array of recording_msid of deleted items
  currPage?: number;
  totalPages: number;
  loading: boolean;
}

export default class MissingMBDataPage extends React.Component<
  MissingMBDataProps,
  MissingMBDataState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private expectedDataPerPage = 25;
  private MissingMBDataTable = React.createRef<HTMLTableElement>();

  constructor(props: MissingMBDataProps) {
    super(props);
    this.state = {
      missingData: props.missingData?.slice(0, this.expectedDataPerPage) || [],
      currPage: 1,
      totalPages: props.missingData
        ? Math.ceil(props.missingData.length / this.expectedDataPerPage)
        : 0,
      loading: false,
      deletedListens: [],
    };

    this.MissingMBDataTable = React.createRef();
  }

  componentDidMount(): void {
    const { currPage } = this.state;
    window.history.replaceState(null, "", `?page=${currPage}`);
  }

  handleClickPrevious = () => {
    const { missingData } = this.props;
    const { currPage } = this.state;
    if (currPage && currPage > 1) {
      this.setState({ loading: true });
      const offset = (currPage - 1) * this.expectedDataPerPage;
      const updatedPage = currPage - 1;
      this.setState(
        {
          missingData:
            missingData?.slice(offset - this.expectedDataPerPage, offset) || [],
          currPage: updatedPage,
        },
        this.afterDisplay
      );
      window.history.pushState(null, "", `?page=${updatedPage}`);
    }
  };

  handleClickNext = () => {
    const { missingData } = this.props;
    const { currPage, totalPages } = this.state;
    if (currPage && currPage < totalPages) {
      this.setState({ loading: true });
      const offset = currPage * this.expectedDataPerPage;
      const updatedPage = currPage + 1;
      this.setState(
        {
          missingData:
            missingData?.slice(offset, offset + this.expectedDataPerPage) || [],
          currPage: updatedPage,
        },
        this.afterDisplay
      );
      window.history.pushState(null, "", `?page=${updatedPage}`);
    }
  };

  afterDisplay = () => {
    if (this.MissingMBDataTable?.current) {
      this.MissingMBDataTable.current.scrollIntoView({ behavior: "smooth" });
    }
    this.setState({ loading: false });
  };

  submitMissingData = (listen: Listen) => {
    // This function submits data to the MusicBrainz server. We have not used
    // fetch here because the endpoint where the submision is being done
    // replies back with HTML and since we cannot redirect via fetch, we have
    // to resort to such obscure method :D
    const { user } = this.props;
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

  deleteListen = async (data: MissingMBData) => {
    const { user } = this.props;
    const { APIService, currentUser } = this.context;
    const isCurrentUser = user.name === currentUser?.name;
    if (isCurrentUser && currentUser?.auth_token) {
      const listenedAt = new Date(data.listened_at).getTime() / 1000;
      try {
        const status = await APIService.deleteListen(
          currentUser.auth_token,
          data.recording_msid,
          listenedAt
        );
        if (status === 200) {
          this.setState((prevState) => ({
            deletedListens: prevState.deletedListens.concat(
              data.recording_msid
            ),
          }));
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

  render() {
    const {
      missingData,
      currPage,
      totalPages,
      loading,
      deletedListens,
    } = this.state;
    const { user } = this.props;
    const { APIService, currentUser } = this.context;
    const isCurrentUser = user.name === currentUser?.name;
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
    return (
      <div className="row" style={{ display: "flex", flexWrap: "wrap" }}>
        <div className="col-xs-12 col-md-8">
          <div>
            <div id="missingMBData" ref={this.MissingMBDataTable}>
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
                if (currentUser?.auth_token) {
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
                    isCurrentUser &&
                    Boolean(listen.listened_at) &&
                    Boolean(recordingMSID);

                  if (canDelete) {
                    additionalMenuItems.push(
                      <ListenControl
                        text="Delete Listen"
                        icon={faTrashAlt}
                        action={this.deleteListen.bind(this, data)}
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
                  onClick={this.handleClickPrevious}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") this.handleClickPrevious();
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
                  onClick={this.handleClickNext}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") this.handleClickNext();
                  }}
                  tabIndex={0}
                >
                  Next &rarr;
                </a>
              </li>
            </ul>
          </div>
        </div>
        <BrainzPlayer
          listens={missingMBDataAsListen}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
        />
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { missingData, user } = reactProps;

  const MissingMBDataPageWithAlertNotification = withAlertNotifications(
    MissingMBDataPage
  );
  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <MissingMBDataPageWithAlertNotification
            missingData={missingData}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
