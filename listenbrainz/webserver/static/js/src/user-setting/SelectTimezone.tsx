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
    };
  }

  zoneSelection = (zone: string): void => {
    this.setState({
      selectZone: zone,
    });
  };

  submitTimezone = async (
    event?: React.FormEvent<HTMLFormElement>
  ): Promise<null> => {
    const { APIService, currentUser } = this.context;
    const { name, auth_token } = currentUser;
    const { selectZone } = this.state;
    const { newAlert } = this.props;

    if (event) {
      event.preventDefault();
    }

    if (auth_token) {
      try {
        const status = await APIService.resetUserTimezone(
          name,
          auth_token,
          selectZone
        );
        if (status === 200) {
          newAlert.bind(this, "success", "Reset timezone", `Reset timezone`);
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error",
          typeof error === "object" ? error?.message : error
        );
      }
    }
    return null;
  };

  render() {
    const { selectZone } = this.state;
    // const { APIService } = this.context;
    const { pg_timezones, user_timezone } = this.props;

    return (
      <>
        <h3>Select Timezone</h3>
        <p>
          Your current timezone setting is{" "}
          {user_timezone ? `${user_timezone}` : "no select"}.
          <br />
          By choosing your local time zone, you will have a local timestamps
          part of your submitted listens. This also informs as when to generate
          daily playlists and other recommendations for you.
        </p>

        <div>
          <form onSubmit={this.submitTimezone}>
            <label>
              {/* {selectZone
                ? `You selected ${selectZone} for your local timezone `
                : "Select you local timezone: "} */}
              Select you local timezone:
            </label>

            <select onChange={(e) => this.zoneSelection(e.target.value)}>
              {/* <select ref="zonename"> */}
              {pg_timezones.map((zone: [string, string]) => {
                return (
                  <option value={zone[0]}>
                    {zone[0]} ({zone[1]})
                  </option>
                );
              })}
            </select>
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
