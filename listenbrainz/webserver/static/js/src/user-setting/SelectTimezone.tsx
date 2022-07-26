import React, { useState } from "react";
import * as ReactDOM from "react-dom";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";

import { getPageProps } from "../utils/utils";
import ErrorBoundary from "../utils/ErrorBoundary";

export type SelectTimezoneProps = {
  pg_timezones: Array<[string, string]>;
  user_timezone: string;
} & WithAlertNotificationsInjectedProps;
export interface SelectTimezoneState {
  selectZone: string;
  userTimezone: string;
}
export default class SelectTimezones extends React.Component<
  SelectTimezoneProps,
  SelectTimezoneState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: SelectTimezoneProps) {
    super(props);
    this.state = {
      selectZone: props.user_timezone,
      userTimezone: props.user_timezone,
    };
  }

  zoneSelection = (zone: string): void => {
    this.setState({
      selectZone: zone,
    });
  };

  submitTimezone = async (
    event?: React.FormEvent<HTMLFormElement>
  ): Promise<any> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { selectZone } = this.state;
    const { newAlert } = this.props;

    if (event) {
      event.preventDefault();
    }

    if (auth_token) {
      try {
        const status = await APIService.resetUserTimezone(
          auth_token,
          selectZone
        );
        if (status === 200) {
          newAlert("success", "Your timezone has been saved.", "");
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error",
          "Something went wrong! Unable to update timezone right now."
        );
      }
    }
    this.setState({
      userTimezone: selectZone,
    });
  };

  render() {
    const { selectZone, userTimezone } = this.state;
    // const { APIService } = this.context;
    const { pg_timezones } = this.props;

    return (
      <>
        <h3>Select Timezone</h3>
        <p>
          Your current timezone setting is{" "}
          <span style={{ fontWeight: "bold" }}>{userTimezone}.</span>
          <br />
          By choosing your local time zone, you will have a local timestamps
          part of your submitted listens. This also informs as when to generate
          daily playlists and other recommendations for you.
        </p>

        <div>
          <form onSubmit={this.submitTimezone}>
            <label>
              Select you local timezone:
              <select
                defaultValue={userTimezone}
                onChange={(e) => this.zoneSelection(e.target.value)}
              >
                <option value="default" disabled>
                  Choose an option
                </option>
                {pg_timezones.map((zone: [string, string]) => {
                  return (
                    <option value={zone[0]}>
                      {zone[0]} ({zone[1]})
                    </option>
                  );
                })}
              </select>
            </label>
            <br />
            <br />
            <p>
              <button type="submit" className="btn btn-info btn-lg">
                Save Timezone
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
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { pg_timezones, user_timezone } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const SelectTimezonesWithAlertNotifications = withAlertNotifications(
    SelectTimezones
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <SelectTimezonesWithAlertNotifications
          initialAlerts={optionalAlerts}
          pg_timezones={pg_timezones}
          user_timezone={user_timezone}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
