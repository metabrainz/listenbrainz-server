import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import { get, isEqual } from "lodash";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "./AlertNotificationsHOC";

import APIServiceClass from "./APIService";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import ErrorBoundary from "./ErrorBoundary";
import Loader from "./components/Loader";
import { getPageProps } from "./utils";
import ListenCard from "./listens/ListenCard";

export type MissingMBDataProps = {
  missingData?: Array<MissingMBData>;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface MissingMBDataState {
  missingData?: Array<MissingMBData>;
  currPage?: number;
  totalPages?: number;
}

export default class MissingMBDataPage extends React.Component<
  MissingMBDataProps,
  MissingMBDataState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private expectedDataPerPage = 25;
  private APIService!: APIServiceClass; // don't know if needed or not
  private MissingMBDataTable = React.createRef<HTMLTableElement>();

  constructor(props: MissingMBDataProps) {
    super(props);
    this.state = {
      missingData: props.missingData?.slice(0, this.expectedDataPerPage) || [],
      currPage: 1,
      totalPages: props.missingData
        ? Math.ceil(props.missingData.length / this.expectedDataPerPage)
        : 0,
    };

    this.MissingMBDataTable = React.createRef();
  }

  componentDidMount(): void {
    const { user } = this.props;
    const { currPage } = this.state;
    const { APIService, currentUser } = this.context;
    this.APIService = APIService;
    window.history.replaceState(null, "", `?page=${currPage}`);
  }

  render() {
    const { missingData, currPage, totalPages } = this.state;
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;
    const isCurrentUser =
      Boolean(currentUser?.name) && currentUser?.name === user?.name;
    return (
      <div role="main">
        <div className="row" style={{ display: "flex", flexWrap: "wrap" }}>
          <div className="col-xs-12">
            <div>
              <div id="missingMBData" ref={this.MissingMBDataTable}>
                <h2>Missing Data:</h2>
                <div>
                  {missingData?.map((data) => {
                    return (
                      <div className="event-content" style={{ width: "100%" }}>
                        <ListenCard
                          key={`${data.recording_name}-${data.artist_name}-${data.listened_at}`}
                          showTimestamp
                          showUsername={false}
                          newAlert={newAlert}
                          isMissingData
                          disablePlay
                          listen={{
                            listened_at:
                              new Date(data.listened_at).getTime() / 1000,
                            user_name: user.name,
                            track_metadata: {
                              artist_name: data.artist_name,
                              track_name: data.recording_name,
                              release_name: data?.release_name,
                            },
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
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

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  const { missingData, user } = reactProps;
  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  const MissingMBDataPageWithAlertNotification = withAlertNotifications(
    MissingMBDataPage
  );
  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <MissingMBDataPageWithAlertNotification
          initialAlerts={optionalAlerts}
          missingData={missingData}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
