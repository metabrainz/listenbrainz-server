import * as React from "react";

import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
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

    if (auth_token) {
      try {
        const status = await APIService.submitTroiPreferences(
          auth_token,
          exportToSpotify
        );
        if (status === 200) {
          this.setState({ exportToSpotify });
          toast.success(
            <ToastMsg
              title="Your playlist preferences have been saved."
              message=""
            />,
            { toastId: "playlist-success" }
          );
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
                <span className="switch label-primary" />
              </label>
            </div>
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
