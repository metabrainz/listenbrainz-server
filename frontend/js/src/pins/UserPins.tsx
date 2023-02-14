/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";

import * as _ from "lodash";

import GlobalAppContext from "../utils/GlobalAppContext";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";

import Loader from "../components/Loader";
import PinnedRecordingCard from "./PinnedRecordingCard";
import {
  getListenablePin,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";

export type UserPinsProps = {
  user: ListenBrainzUser;
  pins: PinnedRecording[];
  totalCount: number;
  profileUrl?: string;
} & WithAlertNotificationsInjectedProps;

export type UserPinsState = {
  pins: PinnedRecording[];
  page: number;
  maxPage: number;
  loading: boolean;
  noMorePins: boolean;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
};

export default class UserPins extends React.Component<
  UserPinsProps,
  UserPinsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private DEFAULT_PINS_PER_PAGE = 25;

  constructor(props: UserPinsProps) {
    super(props);
    const { totalCount } = this.props;
    const maxPage = Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE);
    this.state = {
      maxPage,
      page: 1,
      pins: props.pins || [],
      loading: false,
      noMorePins: maxPage <= 1,
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
    };
  }

  componentDidMount() {
    this.loadFeedback();
  }

  handleLoadMore = async (event?: React.MouseEvent) => {
    const { page, maxPage } = this.state;
    if (page >= maxPage) {
      return;
    }

    await this.getPinsFromAPI(page + 1);
  };

  getPinsFromAPI = async (page: number, replacePinsArray: boolean = false) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    const { pins } = this.state;
    this.setState({ loading: true });

    try {
      const limit = (page - 1) * this.DEFAULT_PINS_PER_PAGE;
      const count = this.DEFAULT_PINS_PER_PAGE;
      const newPins = await APIService.getPinsForUser(user.name, limit, count);

      if (!newPins.pinned_recordings.length) {
        // No pins were fetched
        this.setState({
          loading: false,
          pins: replacePinsArray ? [] : pins,
          noMorePins: true,
        });
        return;
      }

      const totalCount = parseInt(newPins.total_count, 10);
      const newMaxPage = Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE);
      this.setState(
        {
          loading: false,
          page,
          maxPage: newMaxPage,
          pins: replacePinsArray
            ? newPins.pinned_recordings
            : pins.concat(newPins.pinned_recordings),
          noMorePins: page >= newMaxPage,
        },
        this.loadFeedback
      );
    } catch (error) {
      newAlert(
        "warning",
        "Could not load pin history",
        <>
          Something went wrong when we tried to load your pinned recordings,
          please try again or contact us if the problem persists.
          <br />
          <strong>
            {error.name}: {error.message}
          </strong>
        </>
      );
      this.setState({ loading: false });
    }
  };

  getFeedback = async () => {
    const { pins, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    let recording_msids = "";
    let recording_mbids = "";

    if (pins && currentUser?.name) {
      pins.forEach((item) => {
        if (item.recording_msid) {
          recording_msids += `${item.recording_msid},`;
        }
        if (item.recording_mbid) {
          recording_mbids += `${item.recording_mbid},`;
        }
      });
      if (!recording_msids && !recording_mbids) {
        return [];
      }
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recording_msids,
          recording_mbids
        );
        return data.feedback;
      } catch (error) {
        if (newAlert) {
          newAlert(
            "danger",
            "We could not load love/hate feedback",
            typeof error === "object" ? error.message : error
          );
        }
      }
    }
    return [];
  };

  loadFeedback = async () => {
    const feedback = await this.getFeedback();
    if (!feedback) {
      return;
    }
    const recordingMsidFeedbackMap: RecordingFeedbackMap = {};
    const recordingMbidFeedbackMap: RecordingFeedbackMap = {};
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_msid) {
        recordingMsidFeedbackMap[fb.recording_msid] = fb.score;
      }
      if (fb.recording_mbid) {
        recordingMbidFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    this.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
  };

  updateFeedback = (
    recordingMbid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMsid?: string
  ) => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    const newMsidFeedbackMap = { ...recordingMsidFeedbackMap };
    const newMbidFeedbackMap = { ...recordingMbidFeedbackMap };

    if (recordingMsid) {
      newMsidFeedbackMap[recordingMsid] = score as ListenFeedBack;
    }
    if (recordingMbid) {
      newMbidFeedbackMap[recordingMbid] = score as ListenFeedBack;
    }
    this.setState({
      recordingMsidFeedbackMap: newMsidFeedbackMap,
      recordingMbidFeedbackMap: newMbidFeedbackMap,
    });
  };

  getFeedbackForListen = (listen: BaseListenFormat): ListenFeedBack => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    // first check whether the mbid has any feedback available
    // if yes and the feedback is not zero, return it. if the
    // feedback is zero or not the mbid is absent from the map,
    // look for the feedback using the msid.

    const recordingMbid = getRecordingMBID(listen);
    const mbidFeedback = recordingMbid
      ? _.get(recordingMbidFeedbackMap, recordingMbid, 0)
      : 0;

    if (mbidFeedback) {
      return mbidFeedback;
    }

    const recordingMsid = getRecordingMSID(listen);

    return recordingMsid
      ? _.get(recordingMsidFeedbackMap, recordingMsid, 0)
      : 0;
  };

  removePinFromPinsList = (pin: PinnedRecording) => {
    const { pins } = this.state;
    const index = pins.indexOf(pin);

    pins.splice(index, 1);
    this.setState({ pins });
  };

  render() {
    const { user, profileUrl, newAlert } = this.props;
    const { pins, loading, noMorePins } = this.state;
    const { currentUser } = this.context;

    const pinsAsListens = pins.map((pin) => {
      return getListenablePin(pin);
    });

    return (
      <div role="main">
        <h3>
          {user.name === currentUser.name
            ? "Your"
            : `${_.startCase(user.name)}'s`}{" "}
          Pins
        </h3>

        {pins.length === 0 && (
          <>
            <div className="lead text-center">No pins yet</div>

            {user.name === currentUser.name && (
              <>
                Pin one of your
                <a href={`${profileUrl ?? "/my/listens/"}`}> recent Listens!</a>
              </>
            )}
          </>
        )}

        {pins.length > 0 && (
          <div>
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
            <div
              id="pinned-recordings"
              style={{ opacity: loading ? "0.4" : "1" }}
            >
              {pins?.map((pin, index) => {
                return (
                  <PinnedRecordingCard
                    key={pin.created}
                    pinnedRecording={pin}
                    isCurrentUser={currentUser?.name === user?.name}
                    removePinFromPinsList={this.removePinFromPinsList}
                    newAlert={newAlert}
                    currentFeedback={this.getFeedbackForListen(
                      pinsAsListens[index]
                    )}
                    updateFeedbackCallback={this.updateFeedback}
                  />
                );
              })}
              <button
                className={`btn btn-block ${
                  noMorePins ? "btn-default" : "btn-info"
                }`}
                disabled={noMorePins}
                type="button"
                onClick={this.handleLoadMore}
                title="Load more…"
              >
                {noMorePins ? "No more pins to show" : "Load more…"}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
}
