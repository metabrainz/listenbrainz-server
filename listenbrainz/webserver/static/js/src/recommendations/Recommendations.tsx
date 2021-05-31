/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import { get, isEqual } from "lodash";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import BrainzPlayer from "../BrainzPlayer";
import ErrorBoundary from "../ErrorBoundary";
import Loader from "../components/Loader";
import RecommendationCard from "./RecommendationCard";
import { getPageProps } from "../utils";

export type RecommendationsProps = {
  recommendations?: Array<Recommendation>;
  profileUrl?: string;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
} & WithAlertNotificationsInjectedProps;

export interface RecommendationsState {
  currentRecommendation?: Recommendation;
  direction: BrainzPlayDirection;
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

  private brainzPlayer = React.createRef<BrainzPlayer>();
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
      direction: "down",
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
    const { user, newAlert } = this.props;
    const { recommendations } = this.state;
    const recordings: string[] = [];

    if (recommendations) {
      recommendations.forEach((recommendation) => {
        const recordingMbid = get(
          recommendation,
          "track_metadata.additional_info.recording_mbid"
        );
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
        newAlert(
          "danger",
          "Playback error",
          typeof error === "object" ? error.message : error
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
    rating: RecommendationFeedBack | null
  ) => {
    this.setState((state) => ({
      recommendationFeedbackMap: {
        ...state.recommendationFeedbackMap,
        [recordingMbid]: rating,
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

  playRecommendation = (recommendation: Recommendation): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(recommendation);
    }
  };

  handleCurrentRecommendationChange = (
    recommendation: Recommendation | JSPFTrack
  ): void => {
    this.setState({ currentRecommendation: recommendation as Recommendation });
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

  isCurrentRecommendation = (recommendation: Recommendation): boolean => {
    const { currentRecommendation } = this.state;
    return Boolean(
      currentRecommendation && isEqual(recommendation, currentRecommendation)
    );
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
      direction,
      currRecPage,
      totalRecPages,
    } = this.state;
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;

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
                  return (
                    <RecommendationCard
                      key={`${recommendation.track_metadata?.track_name}-${recommendation.track_metadata?.additional_info?.recording_msid}-${recommendation.user_name}`}
                      isCurrentUser={currentUser?.name === user?.name}
                      recommendation={recommendation}
                      playRecommendation={this.playRecommendation}
                      className={`${
                        this.isCurrentRecommendation(recommendation)
                          ? " current-recommendation"
                          : ""
                      }`}
                      currentFeedback={this.getFeedbackForRecordingMbid(
                        recommendation.track_metadata?.additional_info
                          ?.recording_mbid
                      )}
                      updateFeedback={this.updateFeedback}
                      newAlert={newAlert}
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
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <BrainzPlayer
              currentListen={currentRecommendation}
              direction={direction}
              listens={recommendations}
              newAlert={newAlert}
              onCurrentListenChange={this.handleCurrentRecommendationChange}
              ref={this.brainzPlayer}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
  } = globalReactProps;
  const { recommendations, user, web_sockets_server_url } = reactProps;

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  const RecommendationsWithAlertNotifications = withAlertNotifications(
    Recommendations
  );
  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <RecommendationsWithAlertNotifications
          initialAlerts={optionalAlerts}
          recommendations={recommendations}
          user={user}
          webSocketsServerUrl={web_sockets_server_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
