import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import debounce from "lodash/debounce"; // For auto-save debouncing
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
/* This is a class component So not using the useAutoSave hook
as it works for functional components. So using lodash */

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

  // Debounced auto-save function - waits 3 seconds after last change before saving
  private debouncedAutoSave: ReturnType<typeof debounce>;

  constructor(props: SelectTimezoneProps) {
    super(props);

    this.state = {
      selectZone: props.user_timezone,
      userTimezone: props.user_timezone,
    };
    // Creating an debounced  auto save function
    this.debouncedAutoSave = debounce(this.performAutoSave, 3000);
  }

  // Listener for handleBeforeUnload so that pending changes are saved
  // when user tries to close/refresh browser
  componentDidMount(): void {
    window.addEventListener("beforeunload", this.handleBeforeUnload);
  }

  // handles the situation when user naviagtes to another page
  // or click to some link  to move to new page

  componentWillUnmount(): void {
    //  (cleanup)
    window.removeEventListener("beforeunload", this.handleBeforeUnload);
    this.debouncedAutoSave.flush();
  }

  // Fires when user refreshes browser or close the tab
  handleBeforeUnload = (): void => {
    this.debouncedAutoSave.flush();
  };

  zoneSelection = (zone: string): void => {
    this.setState({
      selectZone: zone,
      // if user change again within 3 sec window
      // then the timer again resets
    });
    this.debouncedAutoSave();
  };

  // Main function which performs the auto save
  // This is called 3 seconds after the last timezone change
  performAutoSave = async (): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { selectZone } = this.state;

    // if user is not logged in then dont save
    if (!auth_token) {
      return;
    }

    try {
      // Call API to save timezone
      const status = await APIService.resetUserTimezone(auth_token, selectZone);

      if (status === 200) {
        this.setState({
          userTimezone: selectZone, // Update the displayed timezone
        });

        // Success toast (auto-closes in 3 seconds)
        toast.success("Timezone Saved", { autoClose: 3000 });
      }
    } catch (error) {
      // Error toast (stays visible)
      const errorMessage =
        error instanceof Error ? error.message : "Save failed";
      toast.error(`Error saving timezone: ${errorMessage}`);
    }
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

        <p
          className="border-start border-info border-3 px-3 py-2 mb-3"
          style={{ backgroundColor: "rgba(248, 249, 250)", fontSize: "1.1em" }}
        >
          Changes are saved automatically.
        </p>
        <div>
          <label>
            Select your local timezone:{" "}
            <select
              className="form-select"
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
        </div>
      </>
    );
  }
}

export function SelectTimezoneWrapper() {
  const data = useLoaderData() as SelectTimezoneLoaderData;
  return <SelectTimezone {...data} />;
}
