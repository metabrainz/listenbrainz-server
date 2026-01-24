import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import debounce from "lodash/debounce"; // For auto-save debouncing
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
/* This is a class component So not using the useAutoSave hook
as it works for functional components. So using lodash */
import SaveStatusIndicator from "../../components/SaveStatusIndicator";

export type SelectTimezoneProps = {
  pg_timezones: Array<string[]>;
  user_timezone: string;
};

type SelectTimezoneLoaderData = SelectTimezoneProps;

export interface SelectTimezoneState {
  selectZone: string;
  userTimezone: string;
  saveStatus: "idle" | "saving" | "saved" | "error"; // Track auto-save status
  errorMessage: string;
}

export default class SelectTimezone extends React.Component<
  SelectTimezoneProps,
  SelectTimezoneState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  // Debounced auto-save function - waits 1 seconds after last change before saving
  private debouncedAutoSave: ReturnType<typeof debounce>;

  constructor(props: SelectTimezoneProps) {
    super(props);

    this.state = {
      selectZone: props.user_timezone,
      userTimezone: props.user_timezone,
      saveStatus: "idle", // Initially idle and
      errorMessage: "", // No errors
    };
    // Creating an auto save function -> this waits for 1 sec and then
    // Save the Change
    this.debouncedAutoSave = debounce(this.performAutoSave, 1000);
  }

  componentWillUnmount(): void {
    // Canceling any pending auto-save to prevent memory leaks
    this.debouncedAutoSave.cancel();
  }

  zoneSelection = (zone: string): void => {
    this.setState({
      selectZone: zone,
      // if user change again within 1 sec window
      // then it waits again for 1 sec and then save
    });
    this.debouncedAutoSave();
  };

  // Main function which performs the auto save
  // This is called 1 seconds after the last timezone change
  performAutoSave = async (): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { selectZone } = this.state;

    // if user is not logged in then dont save
    if (!auth_token) {
      return;
    }

    // Show <Saving...> indicator
    this.setState({ saveStatus: "saving" });

    try {
      // Call API to save timezone
      const status = await APIService.resetUserTimezone(auth_token, selectZone);

      if (status === 200) {
        this.setState({
          userTimezone: selectZone, // Update the displayed timezone
          saveStatus: "saved",
          errorMessage: "",
        });

        // Show success toast notification
        toast.success(
          <ToastMsg title="Your timezone has been saved." message="" />,
          { toastId: "timezone-success" }
        );

        // After 1 seconds, hide the "Saved" indicator
        setTimeout(() => {
          this.setState({ saveStatus: "idle" });
        }, 1000);
      }
    } catch (error) {
      // Error occurred -> Show error indicator
      this.setState({
        saveStatus: "error", // Show error icon
        errorMessage: "Save failed",
      });

      // Show error toast notification
      this.handleError(
        error,
        "Auto-save failed! Unable to update timezone right now."
      );
    }
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

    // Cancel any pending auto-save since we're saving manually now
    // this behaviour reduces the API calls to 1 which would be 1 if redundant
    // saving is done , hence now decreasing load on server
    this.debouncedAutoSave.cancel();
    if (auth_token) {
      // Show "Saving..." indicator during manual save
      this.setState({ saveStatus: "saving" });

      try {
        const status = await APIService.resetUserTimezone(
          auth_token,
          selectZone
        );
        if (status === 200) {
          this.setState({
            userTimezone: selectZone,
            saveStatus: "idle", // no indicator for manual save
            errorMessage: "", // clearing any errors
          });
          toast.success(
            <ToastMsg title="Your timezone has been saved." message="" />,
            { toastId: "timezone-success" }
          );
        }
      } catch (error) {
        // Show error indicator on failure
        this.setState({
          saveStatus: "error",
          errorMessage: "Save failed",
        });
        this.handleError(
          error,
          "Something went wrong! Unable to update timezone right now."
        );
      }
    }
  };

  render() {
    const { userTimezone, saveStatus, errorMessage } = this.state; // destructuring
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

        <div>
          <form onSubmit={this.submitTimezone}>
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
            <br />
            <br />
            {/* Show save status indicator - displays saving/saved/error states */}

            <SaveStatusIndicator
              status={saveStatus}
              errorMessage={errorMessage}
            />

            <p>
              <button type="submit" className="btn btn-info btn-lg">
                Save timezone
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
