import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import debounce from "lodash/debounce"; // For auto-save debouncing
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";

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
    };
    // debounced auto save funct.Reset if toggles within 3 sec
    this.debouncedAutoSave = debounce(this.performAutoSave, 3000);
  }

  // Listener for handleBeforeUnload so that pending changes are saved
  // when user tries to close/refresh browser
  componentDidMount(): void {
    window.addEventListener("beforeunload", this.handleBeforeUnload);
  }

  // Handles situation when user naviagtes to another page

  componentWillUnmount(): void {
    //  (cleanup)
    window.removeEventListener("beforeunload", this.handleBeforeUnload);
    this.debouncedAutoSave.flush();
  }

  // Fires when refresh browser or close the tab
  handleBeforeUnload = (): void => {
    this.debouncedAutoSave.flush();
  };

  exportToSpotifySelection = (exportToSpotify: boolean): void => {
    this.setState({ exportToSpotify });
    this.debouncedAutoSave();
  };

  /* Performs the auto-save operation after debounce delay
   This is called 3 seconds after the last preference change */
  performAutoSave = async (): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const { exportToSpotify } = this.state;

    // Don't save if user is not logged in
    if (!currentUser?.auth_token) {
      return;
    }

    try {
      // Call API to save playlist preferences

      const status = await APIService.submitTroiPreferences(
        currentUser?.auth_token,
        exportToSpotify
      );

      if (status === 200) {
        // Success toast (auto-closes in 3 seconds)
        toast.success("Playlist Preferences Saved", {
          autoClose: 3000,
        });
      }
    } catch (error) {
      // Displaying error toast
      const errorMessage =
        error instanceof Error ? error.message : "Save failed";
      toast.error(`Error saving preferences: ${errorMessage}`);
    }
  };

  render() {
    const { exportToSpotify } = this.state;
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
        <p
          className="border-start border-info border-3 px-3 py-2 mb-3"
          style={{ backgroundColor: "rgba(248, 249, 250)", fontSize: "1.1em" }}
        >
          Changes are saved automatically.
        </p>

        <div>
          <div className="preference-switch">
            <input
              id="export-to-spotify"
              name="export-to-spotify"
              type="checkbox"
              onChange={(e) => this.exportToSpotifySelection(e.target.checked)}
              checked={exportToSpotify}
            />
            <label htmlFor="export-to-spotify">
              <b>Auto-export playlists to Spotify</b>
              <span className="switch bg-primary" />
            </label>
          </div>
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
