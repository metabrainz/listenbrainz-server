import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import useAutoSave from "../../hooks/useAutoSave";

export type SelectTimezoneProps = {
  pg_timezones: Array<string[]>;
  user_timezone: string;
  autoSave: (timezone: string) => void;
};

type SelectTimezoneLoaderData = {
  pg_timezones: Array<string[]>;
  user_timezone: string;
};

export interface SelectTimezoneState {
  userTimezone: string;
}

export default class SelectTimezone extends React.Component<
  SelectTimezoneProps,
  SelectTimezoneState
> {
  constructor(props: SelectTimezoneProps) {
    super(props);

    this.state = {
      userTimezone: props.user_timezone,
    };
  }

  // Keep local UI state in sync if the prop value changes.
  componentDidUpdate(prevProps: SelectTimezoneProps) {
    const { user_timezone } = this.props;

    if (prevProps.user_timezone !== user_timezone) {
      this.setState({ userTimezone: user_timezone });
    }
  }

  zoneSelection = (zone: string): void => {
    const { autoSave } = this.props;
    this.setState({
      userTimezone: zone,
    });
    autoSave(zone);
  };

  render() {
    const { userTimezone } = this.state;
    const { pg_timezones } = this.props;

    return (
      <>
        <Helmet>
          <title>Select your timezone</title>
        </Helmet>
        <h3>Select your timezone</h3>
        <p>
          Your timezone is{" "}
          <span style={{ fontWeight: "bold" }}>{userTimezone}.</span>
        </p>

        <p>
          Setting your timezone allows us to generate local timestamps and
          better statistics for your listens. It also influences when your daily
          playlists and recommendations are generated.
        </p>

        <p className="border-start bg-light border-info border-3 px-3 py-2 mb-3 fs-4">
          Changes are saved automatically.
        </p>
        <div>
          <label>
            Select your local timezone:{" "}
            <select
              className="form-select"
              value={userTimezone}
              onChange={(e) => this.zoneSelection(e.target.value)}
            >
              <option value="default" disabled>
                Choose an option
              </option>
              {pg_timezones.map((zone: string[]) => {
                return (
                  <option key={zone[0]} value={zone[0]}>
                    {zone[0]} ({zone[1]})
                  </option>
                );
              })}
            </select>
          </label>
        </div>
      </>
    );
  }
}

export function SelectTimezoneWrapper() {
  const data = useLoaderData() as SelectTimezoneLoaderData;
  const { pg_timezones, user_timezone } = data;

  const globalContext = React.useContext(GlobalAppContext);
  const { APIService, currentUser } = globalContext;

  const submitTimezone = React.useCallback(
    async (newTimezone: string) => {
      if (!currentUser?.auth_token) {
        toast.error("You must be logged in to update your timezone");
        return;
      }

      await APIService.resetUserTimezone(currentUser.auth_token, newTimezone);
    },
    [APIService, currentUser?.auth_token]
  );

  const { triggerAutoSave } = useAutoSave<string>({
    delay: 3000,
    onSave: submitTimezone,
  });

  return (
    <SelectTimezone
      pg_timezones={pg_timezones}
      user_timezone={user_timezone}
      autoSave={triggerAutoSave}
    />
  );
}
