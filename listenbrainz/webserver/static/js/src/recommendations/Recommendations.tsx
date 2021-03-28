/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";

import { get, isEqual } from "lodash";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIService from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import ErrorBoundary from "../ErrorBoundary";
import Loader from "../components/Loader";
import RecommendationCard from "./RecommendationCard";

export type RecommendationsProps = {
  apiUrl: string;
  recommendations?: Array<Recommendation>;
  profileUrl?: string;
  spotify: SpotifyUser;
  youtube: YoutubeUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
  currentUser?: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface RecommendationsState {
  alerts: Array<Alert>;
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
  private brainzPlayer = React.createRef<BrainzPlayer>();
  private recommendationsTable = React.createRef<HTMLTableElement>();
  private APIService: APIService;

  private expectedRecommendationsPerPage = 25;

  constructor(props: RecommendationsProps) {
    super(props);
    this.state = {
      alerts: [],
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
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  componentDidMount(): void {
    const { user, currentUser } = this.props;
    const { currRecPage } = this.state;
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
    const { user, currentUser } = this.props;
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
      alerts,
      currentRecommendation,
      recommendations,
      loading,
      direction,
      currRecPage,
      totalRecPages,
    } = this.state;
    const { spotify, youtube, user, currentUser, apiUrl, newAlert } = this.props;

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
                      currentUser={currentUser}
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
                      apiUrl={apiUrl}
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
              apiService={this.APIService}
              currentListen={currentRecommendation}
              direction={direction}
              listens={recommendations}
              newAlert={newAlert}
              onCurrentListenChange={this.handleCurrentRecommendationChange}
              ref={this.brainzPlayer}
              spotifyUser={spotify}
              youtubeUser={youtube}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // TODO: Show error to the user and ask to reload page
  }
  const {
    api_url,
    recommendations,
    spotify,
    youtube,
    user,
    web_sockets_server_url,
    current_user,
  } = reactProps;
  const RecommendationsWithAlertNotifications = withAlertNotifications(
    Recommendations
  );
  ReactDOM.render(
    <ErrorBoundary>
      <RecommendationsWithAlertNotifications
      apiUrl={api_url}
      recommendations={recommendations}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
      currentUser={current_user}
      youtube={youtube}
    /></ErrorBoundary>,
    domContainer
  );
});
