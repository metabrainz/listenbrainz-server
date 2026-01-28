import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import debounce from "lodash/debounce"; // For auto-save debouncing
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SaveStatusIndicator from "../../components/SaveStatusIndicator"; // Shows save status

type SelectTroiPreferencesProps = {
  exportToSpotify: boolean;
};

type SelectTroiPreferencesLoaderData = {
  troi_prefs: {
    troi: {
      export_to_spotify: boolean;
    };
  };
};

export interface SelectTroiPreferencesState {
  exportToSpotify: boolean;
  // keep the record of  auto-save status
  saveStatus: "idle" | "saving" | "saved" | "error";
  errorMessage: string; // Store error messages for display
}
class SelectTroiPreferences extends React.Component<
  SelectTroiPreferencesProps,
  SelectTroiPreferencesState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  // Debounced auto-save function
  private debouncedAutoSave: ReturnType<typeof debounce>;

  constructor(props: SelectTroiPreferencesProps) {
    super(props);
    this.state = {
      exportToSpotify: props.exportToSpotify,
      saveStatus: "idle", // Start with idle status and
      errorMessage: "", // No errors
    };
    // debounced auto save funct.Reset is r-toggles within 1 sec
    this.debouncedAutoSave = debounce(this.performAutoSave, 1000);
  }

  // Prevents auto-save from firing after component is destroyed
  componentWillUnmount(): void {
    this.debouncedAutoSave.cancel();
  }

  exportToSpotifySelection = (exportToSpotify: boolean): void => {
    this.setState({ exportToSpotify });
    this.debouncedAutoSave();
  };

  /* Performs the auto-save operation after debounce delay
   This is called 1 seconds after the last preference change */
  performAutoSave = async (): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const { exportToSpotify } = this.state;

    // Don't save if user is not logged in
    if (!currentUser?.auth_token) {
      return;
    }

    this.setState({ saveStatus: "saving" });

    try {
      // Call API to save playlist preferences

      const status = await APIService.submitTroiPreferences(
        currentUser?.auth_token,
        exportToSpotify
      );

      if (status === 200) {
        // show "Saved" indicator
        this.setState({
          saveStatus: "saved",
          errorMessage: "", // Clear any previous errors
        });

        // Show success toast notification
        toast.success(
          <ToastMsg
            title="Your playlist preferences have been saved."
            message=""
          />,
          { toastId: "playlist-success" }
        );

        // After 1 seconds, hide the "Saved" indicator
        setTimeout(() => {
          this.setState({ saveStatus: "idle" });
        }, 1000);
      }
    } catch (error) {
      // Error occurred! Show error indicator
      this.setState({
        saveStatus: "error",
        // showing actual error else the generic "Save failed"
        errorMessage: error instanceof Error ? error.message : "Save failed",
      });

      // Show error toast notification
      this.handleError(
        error,
        "Auto-save failed! Unable to update playlist preferences right now."
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
      { toastId: "playlist-error" }
    );
  };

  submitPreferences = async (
    event?: React.FormEvent<HTMLFormElement>
  ): Promise<any> => {
    const { APIService, currentUser } = this.context;
    const { auth_token } = currentUser;
    const { exportToSpotify } = this.state;

    if (event) {
      event.preventDefault();
    }
    // Cancel any pending auto-save since we're saving manually now

    this.debouncedAutoSave.cancel();

    this.setState({ saveStatus: "saving" }); // during manual saving

    if (auth_token) {
      try {
        const status = await APIService.submitTroiPreferences(
          auth_token,
          exportToSpotify
        );
        if (status === 200) {
          this.setState({
            saveStatus: "idle", // Don't show indicator for manual save
            errorMessage: "",
          });

          toast.success(
            <ToastMsg
              title="Your playlist preferences have been saved."
              message=""
            />,
            { toastId: "playlist-success" }
          );
        }
      } catch (error) {
        // Show error indicator on failure
        this.setState({
          saveStatus: "error",
          errorMessage: error instanceof Error ? error.message : "Save failed",
        });
        this.handleError(
          error,
          "Something went wrong! Unable to update playlist preferences right now."
        );
      }
    }
  };

  render() {
    const { exportToSpotify, saveStatus, errorMessage } = this.state;
    return (
      <>
        <Helmet>
          <title>Select Playlist Preferences</title>
        </Helmet>
        <h3>Auto-export playlists</h3>
        <p>
          If auto-export is turned on, ListenBrainz will automatically export
          your generated playlists (Weekly Jams, Weekly Exploration, etc) to
          Spotify.
          <br />
          You can export playlists manually, regardless of whether auto-export
          is turned on or off.
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
                <span className="switch bg-primary" />
              </label>
            </div>
            {/* displays saving/saved/error states */}
            <SaveStatusIndicator
              status={saveStatus}
              errorMessage={errorMessage}
            />
            <p>
              <button type="submit" className="btn btn-info btn-lg">
                Save changes
              </button>
            </p>
          </form>
        </div>
      </>
    );
  }
}

export function SelectTroiPreferencesWrapper() {
  const data = useLoaderData() as SelectTroiPreferencesLoaderData;
  const { troi_prefs } = data;
  const exportToSpotify = troi_prefs?.troi?.export_to_spotify ?? false;
  return <SelectTroiPreferences exportToSpotify={exportToSpotify} />;
}
