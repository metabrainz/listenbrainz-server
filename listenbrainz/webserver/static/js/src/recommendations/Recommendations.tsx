/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import { AlertList } from "react-bs-notifier";
import * as React from "react";
import * as ReactDOM from "react-dom";
import { isEqual } from "lodash";
import BrainzPlayer from "../BrainzPlayer";
import APIService from "../APIService";
import Loader from "../components/Loader";
import RecommendationCard from "./RecommendationCard";

export interface RecommendationsProps {
  apiUrl: string;
  recommendations?: Array<Recommendation>;
  profileUrl?: string;
  spotify: SpotifyUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
  currentUser?: ListenBrainzUser;
}

export interface RecommendationsState {
  alerts: Array<Alert>;
  currentRecommendation?: Recommendation;
  direction: BrainzPlayDirection;
  recommendations: Array<Recommendation>;
  loading: boolean;
  currRecPage?: number;
  totalRecPages: number;
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
    };

    this.recommendationsTable = React.createRef();
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  playRecommendation = (recommendation: Recommendation): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(recommendation);
    }
  };

  handleCurrentRecommendationChange = (
    recommendation: Recommendation
  ): void => {
    this.setState({ currentRecommendation: recommendation });
  };

  newAlert = (
    type: AlertType,
    title: string,
    message?: string | JSX.Element
  ): void => {
    const newAlert = {
      id: new Date().getTime(),
      type,
      title,
      message,
    } as Alert;

    this.setState((prevState) => {
      return {
        alerts: [...prevState.alerts, newAlert],
      };
    });
  };

  onAlertDismissed = (alert: Alert): void => {
    const { alerts } = this.state;

    // find the index of the alert that was dismissed
    const idx = alerts.indexOf(alert);

    if (idx >= 0) {
      this.setState({
        // remove the alert from the array
        alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)],
      });
    }
  };

  handleClickPrevious = () => {
    const { recommendations } = this.props;
    const { currRecPage } = this.state;

    if (currRecPage && currRecPage > 1) {
      this.setState({ loading: true });
      const offset = (currRecPage - 1) * this.expectedRecommendationsPerPage;
      this.setState(
        {
          recommendations:
            recommendations?.slice(
              offset - this.expectedRecommendationsPerPage,
              offset
            ) || [],
          currRecPage: currRecPage - 1,
        },
        this.afterRecommendationsDisplay
      );
      window.history.pushState(null, "", `?page=${currRecPage}`);
    }
  };

  handleClickNext = () => {
    const { recommendations } = this.props;
    const { currRecPage, totalRecPages } = this.state;

    if (currRecPage && currRecPage < totalRecPages) {
      this.setState({ loading: true });
      const offset = currRecPage * this.expectedRecommendationsPerPage;
      this.setState(
        {
          recommendations:
            recommendations?.slice(
              offset,
              offset + this.expectedRecommendationsPerPage
            ) || [],
          currRecPage: currRecPage + 1,
        },
        this.afterRecommendationsDisplay
      );
      window.history.pushState(null, "", `?page=${currRecPage}`);
    }
  };

  isCurrentRecommendation = (recommendation: Recommendation): boolean => {
    const { currentRecommendation } = this.state;
    return Boolean(
      currentRecommendation && isEqual(recommendation, currentRecommendation)
    );
  };

  afterRecommendationsDisplay() {
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
    const { spotify, user, currentUser } = this.props;

    return (
      <div role="main">
        <AlertList
          position="bottom-right"
          alerts={alerts}
          timeout={15000}
          dismissTitle="Dismiss"
          onDismiss={this.onAlertDismissed}
        />
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
              newAlert={this.newAlert}
              onCurrentListenChange={this.handleCurrentRecommendationChange}
              ref={this.brainzPlayer}
              spotifyUser={spotify}
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
    user,
    web_sockets_server_url,
    current_user,
  } = reactProps;

  ReactDOM.render(
    <Recommendations
      apiUrl={api_url}
      recommendations={recommendations}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
      currentUser={current_user}
    />,
    domContainer
  );
});
