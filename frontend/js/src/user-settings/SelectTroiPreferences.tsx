import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";

export type SelectTroiPreferencesProps = {
  exportToSpotify: boolean;
} & WithAlertNotificationsInjectedProps;

export interface SelectTroiPreferencesState {
  exportToSpotify: boolean;
}
class SelectTroiPreferences extends React.Component<
  SelectTroiPreferencesProps,
  SelectTroiPreferencesState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: SelectTroiPreferencesProps) {
    super(props);
    this.state = {
      exportToSpotify: props.exportToSpotify,
    };
  }

  exportToSpotifySelection = (exportToSpotify: boolean): void => {
    this.setState({ exportToSpotify });
  };

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  submitPreferences = async (
    event?: React.FormEvent<HTMLFormElement>
  ): Promise<any> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { exportToSpotify } = this.state;
    const { newAlert } = this.props;

    if (event) {
      event.preventDefault();
    }

    if (auth_token) {
      try {
        const status = await APIService.submitTroiPreferences(
          auth_token,
          exportToSpotify
        );
        if (status === 200) {
          this.setState({ exportToSpotify });
          newAlert("success", "Your playlist preferences have been saved.", "");
        }
      } catch (error) {
        this.handleError(
          error,
          "Something went wrong! Unable to update playlist preferences right now."
        );
      }
    }
  };

  render() {
    const { exportToSpotify } = this.state;

    return (
      <>
        <h3>Configure auto export of daily jams playlists</h3>
        <p>
          If this setting is turned on, ListenBrainz will automatically export
          your daily jams playlists to Spotify everyday.
          <br />
          You can always export playlists manually regardless of whether this
          setting is turned on or off.
        </p>

        <div>
          <form onSubmit={this.submitPreferences}>
            <div className="preference-switch">
              <input
                id="export-to-spotify"
                name="export-to-spotify"
                type="checkbox"
                onChange={(e) =>
                  this.exportToSpotifySelection(e.target.checked)
                }
                checked={exportToSpotify}
              />
              <label htmlFor="export-to-spotify">
                <b>Auto-export playlists to Spotify</b>
                <span className="switch label-primary" />
              </label>
            </div>
            <p>
              <button type="submit" className="btn btn-info btn-lg">
                Save Changes
              </button>
            </p>
          </form>
        </div>
      </>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
    optionalAlerts,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const { troi_prefs } = reactProps;
  const exportToSpotify = troi_prefs?.troi?.export_to_spotify ?? false;

  const SelectTroiPreferencesWithAlertNotifications = withAlertNotifications(
    SelectTroiPreferences
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <SelectTroiPreferencesWithAlertNotifications
          initialAlerts={optionalAlerts}
          exportToSpotify={exportToSpotify}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
