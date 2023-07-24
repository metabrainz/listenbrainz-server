/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";

import { get, isEqual, isInteger } from "lodash";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../utils/GlobalAppContext";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import Loader from "../components/Loader";
import {
  fullLocalizedDateFromTimestampOrISODate,
  getArtistName,
  getPageProps,
  getRecordingMBID,
  getTrackName,
  preciseTimestamp,
} from "../utils/utils";
import ListenCard from "../listens/ListenCard";
import RecommendationFeedbackComponent from "../listens/RecommendationFeedbackComponent";
import { ToastMsg } from "../notifications/Notifications";

export type RecommendationsProps = {
  recommendations?: Array<Recommendation>;
  user: ListenBrainzUser;
};

export interface RecommendationsState {
  currentRecommendation?: Recommendation;
  recommendations: Array<Recommendation>;
  loading: boolean;
  currRecPage?: number;
  totalRecPages: number;
  recommendationFeedbackMap: RecommendationFeedbackMap;
}

export default class Recommendations extends React.Component<
  RecommendationsProps,
  RecommendationsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private recommendationsTable = React.createRef<HTMLTableElement>();

  private APIService!: APIServiceClass;

  private expectedRecommendationsPerPage = 25;

  constructor(props: RecommendationsProps) {
    super(props);
    this.state = {
      recommendations:
        props.recommendations?.slice(0, this.expectedRecommendationsPerPage) ||
        [],
      loading: false,
      currRecPage: 1,
      totalRecPages: props.recommendations
        ? Math.ceil(
            props.recommendations.length / this.expectedRecommendationsPerPage
          )
        : 0,
      recommendationFeedbackMap: {},
    };

    this.recommendationsTable = React.createRef();
  }

  componentDidMount(): void {
    const { user } = this.props;
    const { currRecPage } = this.state;
    const { APIService, currentUser } = this.context;
    this.APIService = APIService;
    if (currentUser?.name === user?.name) {
      this.loadFeedback();
    }
    window.history.replaceState(null, "", `?page=${currRecPage}`);
  }

  getFeedback = async () => {
    const { user } = this.props;
    const { recommendations } = this.state;
    const recordings: string[] = [];

    if (recommendations) {
      recommendations.forEach((recommendation) => {
        const recordingMbid = getRecordingMBID(recommendation);
        if (recordingMbid) {
          recordings.push(recordingMbid);
        }
      });
      try {
        const data = await this.APIService.getFeedbackForUserForRecommendations(
          user.name,
          recordings.join(",")
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          <ToastMsg
            title="We could not load love/hate feedback"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "load-feedback-error" }
        );
      }
    }
    return [];
  };

  loadFeedback = async () => {
    const feedback = await this.getFeedback();
    if (!feedback) {
      return;
    }
    const recommendationFeedbackMap: RecommendationFeedbackMap = {};
    feedback.forEach((fb: RecommendationFeedbackResponse) => {
      recommendationFeedbackMap[fb.recording_mbid] = fb.rating;
    });
    this.setState({ recommendationFeedbackMap });
  };

  updateFeedback = (
    recordingMbid: string,
    rating: ListenFeedBack | RecommendationFeedBack | null
  ) => {
    this.setState((state) => ({
      recommendationFeedbackMap: {
        ...state.recommendationFeedbackMap,
        [recordingMbid]: rating as RecommendationFeedBack,
      },
    }));
  };

  getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): RecommendationFeedBack | null => {
    const { recommendationFeedbackMap } = this.state;
    return recordingMbid
      ? get(recommendationFeedbackMap, recordingMbid, null)
      : null;
  };

  handleClickPrevious = () => {
    const { recommendations } = this.props;
    const { currRecPage } = this.state;

    if (currRecPage && currRecPage > 1) {
      this.setState({ loading: true });
      const offset = (currRecPage - 1) * this.expectedRecommendationsPerPage;
      const updatedRecPage = currRecPage - 1;
      this.setState(
        {
          recommendations:
            recommendations?.slice(
              offset - this.expectedRecommendationsPerPage,
              offset
            ) || [],
          currRecPage: updatedRecPage,
        },
        this.afterRecommendationsDisplay
      );
      window.history.pushState(null, "", `?page=${updatedRecPage}`);
    }
  };

  handleClickNext = () => {
    const { recommendations } = this.props;
    const { currRecPage, totalRecPages } = this.state;

    if (currRecPage && currRecPage < totalRecPages) {
      this.setState({ loading: true });
      const offset = currRecPage * this.expectedRecommendationsPerPage;
      const updatedRecPage = currRecPage + 1;
      this.setState(
        {
          recommendations:
            recommendations?.slice(
              offset,
              offset + this.expectedRecommendationsPerPage
            ) || [],
          currRecPage: updatedRecPage,
        },
        this.afterRecommendationsDisplay
      );
      window.history.pushState(null, "", `?page=${updatedRecPage}`);
    }
  };

  afterRecommendationsDisplay() {
    const { currentUser } = this.context;
    const { user } = this.props;
    if (currentUser?.name === user?.name) {
      this.loadFeedback();
    }
    if (this.recommendationsTable?.current) {
      this.recommendationsTable.current.scrollIntoView({ behavior: "smooth" });
    }
    this.setState({ loading: false });
  }

  render() {
    const {
      currentRecommendation,
      recommendations,
      loading,
      currRecPage,
      totalRecPages,
    } = this.state;
    const { user } = this.props;
    const { APIService, currentUser } = this.context;
    const isCurrentUser =
      Boolean(currentUser?.name) && currentUser?.name === user?.name;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
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
                id="recommendations"
                ref={this.recommendationsTable}
                style={{ opacity: loading ? "0.4" : "1" }}
              >
                {recommendations.map((recommendation) => {
                  const recordingMBID = getRecordingMBID(recommendation);
                  const recommendationFeedbackComponent = (
                    <RecommendationFeedbackComponent
                      updateFeedbackCallback={this.updateFeedback}
                      listen={recommendation}
                      currentFeedback={this.getFeedbackForRecordingMbid(
                        recordingMBID
                      )}
                    />
                  );
                  // Backwards compatible support for various timestamp property names
                  let discoveryTimestamp: string | number | undefined | null =
                    recommendation.latest_listened_at;
                  if (!discoveryTimestamp) {
                    discoveryTimestamp = recommendation.listened_at_iso;
                  }
                  if (
                    !discoveryTimestamp &&
                    isInteger(recommendation.listened_at)
                  ) {
                    // Transfrom unix timestamp in JS milliseconds timestamp
                    discoveryTimestamp = recommendation.listened_at * 1000;
                  }
                  const customTimestamp = discoveryTimestamp ? (
                    <span
                      className="listen-time"
                      title={fullLocalizedDateFromTimestampOrISODate(
                        discoveryTimestamp
                      )}
                    >
                      Last listened at
                      <br />
                      {preciseTimestamp(discoveryTimestamp)}
                    </span>
                  ) : (
                    <span className="listen-time">Not listened to yet</span>
                  );
                  return (
                    <ListenCard
                      key={`${getTrackName(recommendation)}-${getArtistName(
                        recommendation
                      )}`}
                      customTimestamp={customTimestamp}
                      showTimestamp
                      showUsername={false}
                      feedbackComponent={recommendationFeedbackComponent}
                      listen={recommendation}
                    />
                  );
                })}
              </div>
              <ul className="pager" style={{ display: "flex" }}>
                <li
                  className={`previous ${
                    currRecPage && currRecPage <= 1 ? "hidden" : ""
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
                    currRecPage && currRecPage >= totalRecPages ? "hidden" : ""
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

            <br />
          </div>
          <BrainzPlayer
            listens={recommendations}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
        </div>
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
  const { recommendations, user } = reactProps;

  const RecommendationsWithAlertNotifications = withAlertNotifications(
    Recommendations
  );
  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <RecommendationsWithAlertNotifications
            recommendations={recommendations}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
