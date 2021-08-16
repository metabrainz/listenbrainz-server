/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";

import { isEqual } from "lodash";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import Loader from "../components/Loader";
import PinnedRecordingCard from "../PinnedRecordingCard";
import { getPageProps, getListenablePin } from "../utils";

export type UserPinsProps = {
  user: ListenBrainzUser;
  pins: PinnedRecording[];
  totalCount: number;
  profileUrl?: string;
} & WithAlertNotificationsInjectedProps;

export type UserPinsState = {
  direction: BrainzPlayDirection;
  currentListen?: Listen;
  pins: PinnedRecording[];
  page: number;
  maxPage: number;
  loading: boolean;
};

export default class UserPins extends React.Component<
  UserPinsProps,
  UserPinsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private brainzPlayer = React.createRef<BrainzPlayer>();
  private DEFAULT_PINS_PER_PAGE = 25;

  constructor(props: UserPinsProps) {
    super(props);
    const { totalCount } = this.props;
    this.state = {
      maxPage: 2,
      page: Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE),
      pins: props.pins || [],
      loading: false,
      direction: "down",
    };
  }

  async componentDidMount(): Promise<void> {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    this.handleURLChange();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  getFeedFromAPI = async (page: number) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    this.setState({ loading: true });

    try {
      const newPins = await APIService.getPinsForUser(
        user.name,
        (page - 1) * this.DEFAULT_PINS_PER_PAGE,
        this.DEFAULT_PINS_PER_PAGE
      );

      this.handleAPIResponse(newPins, page, () => {
        window.history.pushState(null, "", `?page=${page}`);
      });
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

  handleAPIResponse = (
    newPins: {
      pinned_recordings: PinnedRecording[];
      total_count: string;
      count: string;
      offset: string;
    },
    page: number,
    successCallback?: () => void
  ) => {
    const parsedTotalCount = parseInt(newPins.total_count, 10);

    this.setState(
      {
        loading: false,
        page,
        maxPage: Math.ceil(parsedTotalCount / this.DEFAULT_PINS_PER_PAGE),
        pins: newPins.pinned_recordings,
      },
      successCallback
    );

    // Scroll window back to the top of the events container element
    const eventContainerElement = document.querySelector("#pinned-recordings");
    if (eventContainerElement) {
      eventContainerElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  handleURLChange = async (): Promise<void> => {
    const { maxPage } = this.state;
    const url = new URL(window.location.href);

    if (url.searchParams.get("page")) {
      let page = Number(url.searchParams.get("page"));
      if (page <= 0 || page >= maxPage) {
        page = 1;
      } else if (page >= maxPage) {
        page = maxPage;
      }
      await this.getFeedFromAPI(page);
    } else {
      this.setState({ page: 1 });
    }
  };

  // pagination functions
  handleClickOlder = async (event?: React.MouseEvent) => {
    const { page, maxPage } = this.state;

    if (event) {
      event.preventDefault();
    }
    if (page >= maxPage) {
      return;
    }

    await this.getFeedFromAPI(page + 1);
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    const { page } = this.state;

    if (event) {
      event.preventDefault();
    }
    if (page === 1) {
      return;
    }

    await this.getFeedFromAPI(page - 1);
  };

  // BrainzPlayer functions
  removePinFromPinsList = (pin: PinnedRecording) => {
    const { pins } = this.state;
    const index = pins.indexOf(pin);

    pins.splice(index, 1);
    this.setState({ pins });
  };

  handleCurrentListenChange = (listen: Listen | JSPFTrack): void => {
    this.setState({ currentListen: listen as Listen });
  };

  isCurrentListen = (listen: Listen): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && isEqual(listen, currentListen));
  };

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  render() {
    const { user, profileUrl, newAlert } = this.props;
    const {
      pins,
      page,
      direction,
      loading,
      currentListen,
      maxPage,
    } = this.state;
    const { currentUser } = this.context;

    const isNewerButtonDisabled = page === 1;
    const isOlderButtonDisabled = page >= maxPage;

    const pinsAsListens = pins.map((pin) => {
      return getListenablePin(pin);
    });

    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <h3>Pinned Recordings</h3>

            {pins.length === 0 && (
              <>
                <div className="lead text-center">No pins yet</div>

                {user.name === currentUser.name && (
                  <>
                    Pin one of your
                    <a href={`${profileUrl}`}> recent Listens!</a>
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
                  {pins?.map((pin) => {
                    return (
                      <PinnedRecordingCard
                        userName={user.name}
                        pinnedRecording={pin}
                        className={
                          this.isCurrentListen(getListenablePin(pin))
                            ? " current-listen"
                            : ""
                        }
                        isCurrentUser={currentUser?.name === user?.name}
                        playListen={this.playListen}
                        removePinFromPinsList={this.removePinFromPinsList}
                        newAlert={newAlert}
                      />
                    );
                  })}

                  {pins.length < this.DEFAULT_PINS_PER_PAGE && (
                    <h5 className="text-center">No more pins to show.</h5>
                  )}
                </div>

                <ul
                  className="pager"
                  id="navigation"
                  style={{ marginRight: "-1em", marginLeft: "1.5em" }}
                >
                  <li
                    className={`previous ${
                      isNewerButtonDisabled ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewer}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewer();
                      }}
                      tabIndex={0}
                    >
                      &larr; Newer
                    </a>
                  </li>
                  <li
                    className={`next ${
                      isOlderButtonDisabled ? "disabled" : ""
                    }`}
                    style={{ marginLeft: "auto" }}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickOlder}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOlder();
                      }}
                      tabIndex={0}
                    >
                      Older &rarr;
                    </a>
                  </li>
                </ul>
              </div>
            )}
          </div>
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <BrainzPlayer
              currentListen={currentListen}
              direction={direction}
              listens={pinsAsListens}
              newAlert={newAlert}
              onCurrentListenChange={this.handleCurrentListenChange}
              ref={this.brainzPlayer}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user, pins, total_count, profile_url } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const UserPinsWithAlertNotifications = withAlertNotifications(UserPins);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserPinsWithAlertNotifications
          user={user}
          pins={pins}
          totalCount={total_count}
          profileUrl={profile_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
