/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faHeart, faHeartCrack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import Pill from "../../../components/Pill";
import ListenCard from "../../../common/listens/ListenCard";
import Loader from "../../../components/Loader";
import { ToastMsg } from "../../../notifications/Notifications";
import { getRecordingMBID, getRecordingMSID } from "../../../utils/utils";

export type UserFeedbackProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalCount: number;
  user: ListenBrainzUser;
};

export interface UserFeedbackState {
  feedback: Array<FeedbackResponseWithTrackMetadata>;
  loading: boolean;
  noMoreFeedback: boolean;
  page: number;
  maxPage: number;
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
      selectedFeedbackScore: feedback?.[0]?.score ?? 1,
      noMoreFeedback: maxPage <= 1,
    };
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
    const { user } = this.props;
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
      this.setState({
        loading: false,
        page,
        maxPage: newMaxPage,
        noMoreFeedback: page >= newMaxPage,
        feedback: replaceFeebackArray
          ? feedbackResponse.feedback
          : feedback.concat(feedbackResponse.feedback),
      });
    } catch (error) {
      toast.warn(
        <ToastMsg
          title="We could not load love/hate feedback"
          message={
            <>
              Something went wrong when we tried to load your loved/hated
              recordings, please try again or contact us if the problem
              persists.
              <br />
              <strong>
                {error.name}: {error.message}
              </strong>
            </>
          }
        />,
        { toastId: "load-feedback-error" }
      );
      this.setState({ loading: false });
    }
  };

  changeSelectedFeedback = (newFeedbackLevel: ListenFeedBack) => {
    this.setState(
      { selectedFeedbackScore: newFeedbackLevel },
      this.getFeedbackItemsFromAPI.bind(this, 1, true)
    );
  };

  render() {
    const {
      feedback,
      loading,
      maxPage,
      page,
      selectedFeedbackScore,
    } = this.state;
    const { user } = this.props;
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
        <div className="listen-header pills">
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
            <FontAwesomeIcon icon={faHeartCrack as IconProp} /> Hated
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
            <div
              id="listens"
              role="list"
              data-testid="userfeedback-listens"
              style={{ opacity: loading ? "0.4" : "1" }}
            >
              {listensFromFeedback.map((listen) => {
                const recording_msid = getRecordingMSID(listen);
                const recording_mbid = getRecordingMBID(listen);
                return (
                  <ListenCard
                    showUsername={false}
                    showTimestamp
                    key={`${listen.listened_at}-${recording_msid}-${recording_mbid}`}
                    listen={listen}
                  />
                );
              })}
            </div>
            <button
              className={`mt-15 btn btn-block ${
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
