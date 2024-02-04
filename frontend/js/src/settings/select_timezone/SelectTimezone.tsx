import * as React from "react";

import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";

export type SelectTimezoneProps = {
  pg_timezones: Array<string[]>;
  user_timezone: string;
};

type SelectTimezoneLoaderData = SelectTimezoneProps;

export interface SelectTimezoneState {
  selectZone: string;
  userTimezone: string;
}

export default class SelectTimezone extends React.Component<
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

  handleError = (error: string | Error, title?: string): void => {
    if (!error) {
      return;
    }
    toast.error(
      <ToastMsg
        title={title || "Error"}
        message={typeof error === "object" ? error.message : error}
      />,
      { toastId: "timezone-success" }
    );
  };

  submitTimezone = async (
    event?: React.FormEvent<HTMLFormElement>
  ): Promise<any> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { selectZone } = this.state;

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
          this.setState({
            userTimezone: selectZone,
          });
          toast.success(
            <ToastMsg title="Your timezone has been saved." message="" />,
            { toastId: "timezone-success" }
          );
        }
      } catch (error) {
        this.handleError(
          error,
          "Something went wrong! Unable to update timezone right now."
        );
      }
    }
  };

  render() {
    const { userTimezone } = this.state;
    const { pg_timezones } = this.props;

    return (
      <>
        <Helmet>
          <title>Select Timezone- ListenBrainz</title>
        </Helmet>
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
              Select your local timezone:
              <select
                defaultValue={userTimezone}
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

export function SelectTimezoneWrapper() {
  const data = useLoaderData() as SelectTimezoneLoaderData;
  return <SelectTimezone {...data} />;
}

export const SelectTimezoneLoader = async () => {
  const response = await fetch("/settings/select_timezone/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return data;
};
