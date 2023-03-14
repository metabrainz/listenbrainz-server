/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faHeart,
  faHeartBroken,
  faThumbtack,
} from "@fortawesome/free-solid-svg-icons";
import { clone, get, has, isNaN } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";

import Pill from "../components/Pill";
import ListenCard from "../listens/ListenCard";
import Loader from "../components/Loader";
import {
  getRecordingMBID,
  getRecordingMSID,
  handleNavigationClickEvent,
} from "../utils/utils";
import ListenControl from "../listens/ListenControl";

export type UserFeedbackProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalCount: number;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface UserFeedbackState {
  feedback: Array<FeedbackResponseWithTrackMetadata>;
  loading: boolean;
  noMoreFeedback: boolean;
  page: number;
  maxPage: number;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
  selectedFeedbackScore: ListenFeedBack;
}

export default class UserFeedback extends React.Component<
  UserFeedbackProps,
  UserFeedbackState
> {
  static contextType = GlobalAppContext;
  static RecordingMetadataToListenFormat = (
    feedbackItem: FeedbackResponseWithTrackMetadata
  ): Listen => {
    return {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
  };

  declare context: React.ContextType<typeof GlobalAppContext>;
  private DEFAULT_ITEMS_PER_PAGE = 25;

  constructor(props: UserFeedbackProps) {
    super(props);
    const { totalCount, feedback } = props;
    const maxPage = Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE);
    this.state = {
      maxPage,
      page: 1,
      feedback: feedback?.slice(0, this.DEFAULT_ITEMS_PER_PAGE) || [],
      loading: false,
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
      selectedFeedbackScore: feedback?.[0]?.score ?? 1,
      noMoreFeedback: maxPage <= 1,
    };
  }

  componentDidMount(): void {
    const { currentUser } = this.context;
    const { user, feedback } = this.props;

    if (currentUser?.name === user.name && feedback?.length) {
      // Logged in user is looking at their own feedback, we can build
      // the recordingMsidFeedbackMap from feedback which already contains the feedback score for each item
      const recordingMsidFeedbackMap: RecordingFeedbackMap = {};
      const recordingMbidFeedbackMap: RecordingFeedbackMap = {};

      feedback.forEach((item) => {
        if (item.recording_msid) {
          recordingMsidFeedbackMap[item.recording_msid] = item.score;
        }
        if (item.recording_mbid) {
          recordingMbidFeedbackMap[item.recording_mbid] = item.score;
        }
      });
      this.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
    } else {
      this.loadFeedback();
    }
  }

  handleLoadMore = async (event?: React.MouseEvent) => {
    const { page, maxPage } = this.state;
    if (page >= maxPage) {
      return;
    }

    await this.getFeedbackItemsFromAPI(page + 1);
  };

  getFeedbackItemsFromAPI = async (
    page: number,
    replaceFeebackArray: boolean = false
  ) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    const { selectedFeedbackScore, feedback } = this.state;
    this.setState({ loading: true });

    try {
      const offset = (page - 1) * this.DEFAULT_ITEMS_PER_PAGE;
      const count = this.DEFAULT_ITEMS_PER_PAGE;
      const feedbackResponse = await APIService.getFeedbackForUser(
        user.name,
        offset,
        count,
        selectedFeedbackScore
      );

      if (!feedbackResponse?.feedback?.length) {
        // No pins were fetched
        this.setState({
          loading: false,
          feedback: replaceFeebackArray ? [] : feedback,
          noMoreFeedback: true,
        });
        return;
      }

      const totalCount = parseInt(feedbackResponse.total_count, 10);
      const newMaxPage = Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE);
      this.setState(
        {
          loading: false,
          page,
          maxPage: newMaxPage,
          noMoreFeedback: page >= newMaxPage,
          feedback: replaceFeebackArray
            ? feedbackResponse.feedback
            : feedback.concat(feedbackResponse.feedback),
        },
        this.loadFeedback
      );
    } catch (error) {
      newAlert(
        "warning",
        "We could not load love/hate feedback",
        <>
          Something went wrong when we tried to load your loved/hated
          recordings, please try again or contact us if the problem persists.
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
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const {
      feedback,
      recordingMsidFeedbackMap,
      recordingMbidFeedbackMap,
    } = this.state;

    let recording_msids = "";
    let recording_mbids = "";
    if (feedback?.length && currentUser?.name) {
      recording_msids = feedback
        .map((item) => item.recording_msid)
        // Only request non-undefined and non-empty string
        .filter(Boolean)
        // Only request feedback we don't already have
        .filter((msid) => !has(recordingMsidFeedbackMap, msid))
        .join(",");
      recording_mbids = feedback
        .map((item) => item.recording_mbid)
        // Only request non-undefined and non-empty string
        .filter(Boolean)
        // Only request feedback we don't already have
        // @ts-ignore
        .filter((mbid) => !has(recordingMbidFeedbackMap, mbid))
        .join(",");
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
            "warning",
            "We could not load love/hate feedback",
            typeof error === "object" ? error.message : error
          );
        }
      }
    }
    return [];
  };

  changeSelectedFeedback = (newFeedbackLevel: ListenFeedBack) => {
    this.setState(
      { selectedFeedbackScore: newFeedbackLevel },
      this.getFeedbackItemsFromAPI.bind(this, 1, true)
    );
  };

  loadFeedback = async () => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;
    const feedback = await this.getFeedback();
    if (!feedback?.length) {
      return;
    }
    const newRecordingMsidFeedbackMap: RecordingFeedbackMap = {
      ...recordingMsidFeedbackMap,
    };
    const newRecordingMbidFeedbackMap: RecordingFeedbackMap = {
      ...recordingMbidFeedbackMap,
    };
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_msid) {
        newRecordingMsidFeedbackMap[fb.recording_msid] = fb.score;
      }
      if (fb.recording_mbid) {
        newRecordingMbidFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    this.setState({
      recordingMsidFeedbackMap: newRecordingMsidFeedbackMap,
      recordingMbidFeedbackMap: newRecordingMbidFeedbackMap,
    });
  };

  updateFeedback = (
    recordingMbid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMsid?: string
  ) => {
    const {
      recordingMsidFeedbackMap,
      recordingMbidFeedbackMap,
      feedback,
    } = this.state;
    const { currentUser } = this.context;
    const { user } = this.props;

    const newFeedbackMsidMap = {
      ...recordingMsidFeedbackMap,
    };
    const newFeedbackMbidMap = {
      ...recordingMbidFeedbackMap,
    };
    if (recordingMsid) {
      newFeedbackMsidMap[recordingMsid] = score as ListenFeedBack;
    }
    if (recordingMbid) {
      newFeedbackMbidMap[recordingMbid] = score as ListenFeedBack;
    }

    if (currentUser?.name && currentUser.name === user?.name) {
      const index = feedback.findIndex(
        (feedbackItem) =>
          feedbackItem.recording_msid === recordingMsid ||
          feedbackItem.recording_mbid === recordingMbid
      );
      const newFeedbackArray = clone(feedback);
      newFeedbackArray.splice(index, 1);
      this.setState({
        recordingMsidFeedbackMap: newFeedbackMsidMap,
        recordingMbidFeedbackMap: newFeedbackMbidMap,
        feedback: newFeedbackArray,
      });
    } else {
      this.setState({
        recordingMsidFeedbackMap: newFeedbackMsidMap,
        recordingMbidFeedbackMap: newFeedbackMbidMap,
      });
    }
  };

  getFeedbackForListen = (listen: BaseListenFormat): ListenFeedBack => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    // first check whether the mbid has any feedback available
    // if yes and the feedback is not zero, return it. if the
    // feedback is zero or not the mbid is absent from the map,
    // look for the feedback using the msid.

    const recordingMbid = getRecordingMBID(listen);
    const mbidFeedback = recordingMbid
      ? get(recordingMbidFeedbackMap, recordingMbid, 0)
      : 0;

    if (mbidFeedback) {
      return mbidFeedback;
    }

    const recordingMsid = getRecordingMSID(listen);

    return recordingMsid ? get(recordingMsidFeedbackMap, recordingMsid, 0) : 0;
  };

  render() {
    const {
      feedback,
      loading,
      maxPage,
      page,
      selectedFeedbackScore,
    } = this.state;
    const { user, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const { noMoreFeedback } = this.state;
    const listensFromFeedback: BaseListenFormat[] = feedback
      // remove feedback items for which track metadata wasn't found. this usually means bad
      // msid or mbid data was submitted by the user.
      .filter((item) => item?.track_metadata)
      .map((feedbackItem) =>
        UserFeedback.RecordingMetadataToListenFormat(feedbackItem)
      );

    return (
      <div>
        <div style={{ marginTop: "1em" }}>
          <Pill
            active={selectedFeedbackScore === 1}
            type="secondary"
            onClick={() => this.changeSelectedFeedback(1)}
          >
            <FontAwesomeIcon icon={faHeart as IconProp} /> Loved
          </Pill>
          <Pill
            active={selectedFeedbackScore === -1}
            type="secondary"
            onClick={() => this.changeSelectedFeedback(-1)}
          >
            <FontAwesomeIcon icon={faHeartBroken as IconProp} /> Hated
          </Pill>
        </div>
        {!feedback.length && (
          <div className="lead text-center">
            <p>
              No {selectedFeedbackScore === 1 ? "loved" : "hated"} tracks to
              show yet
            </p>
          </div>
        )}
        {feedback.length > 0 && (
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
            <div id="listens" style={{ opacity: loading ? "0.4" : "1" }}>
              {listensFromFeedback.map((listen) => {
                const recording_msid = getRecordingMSID(listen);
                const recording_mbid = getRecordingMBID(listen);
                return (
                  <ListenCard
                    showUsername={false}
                    showTimestamp
                    key={`${listen.listened_at}-${recording_msid}-${recording_mbid}`}
                    listen={listen}
                    currentFeedback={this.getFeedbackForListen(listen)}
                    updateFeedbackCallback={this.updateFeedback}
                    newAlert={newAlert}
                  />
                );
              })}
            </div>
            <button
              className={`btn btn-block ${
                noMoreFeedback ? "btn-default" : "btn-info"
              }`}
              disabled={noMoreFeedback}
              type="button"
              onClick={this.handleLoadMore}
              title="Load more…"
            >
              {noMoreFeedback ? "No more feedback to show" : "Load more…"}
            </button>
          </div>
        )}
      </div>
    );
  }
}
