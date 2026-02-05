import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import useAutoSave from "../../hooks/useAutoSave";

type SelectTroiPreferencesProps = {
  exportToSpotify: boolean;
  autoSave: (exportToSpotify: boolean) => void;
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
  constructor(props: SelectTroiPreferencesProps) {
    super(props);
    this.state = {
      exportToSpotify: props.exportToSpotify,
    };
  }

  // Keep local UI state in sync if the prop value changes.

  componentDidUpdate(prevProps: SelectTroiPreferencesProps) {
    const { exportToSpotify } = this.props;

    if (prevProps.exportToSpotify !== exportToSpotify) {
      this.setState({ exportToSpotify });
    }
  }

  exportToSpotifySelection = (exportToSpotify: boolean): void => {
    const { autoSave } = this.props;
    this.setState({ exportToSpotify });
    autoSave(exportToSpotify);
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
        <p className="border-start  bg-light border-info border-3 px-3 py-2 mb-3 fs-4">
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

//  Functional wrapper

export function SelectTroiPreferencesWrapper() {
  const data = useLoaderData() as SelectTroiPreferencesLoaderData;
  const exportToSpotify = data?.troi_prefs?.troi?.export_to_spotify ?? false;

  const globalContext = React.useContext(GlobalAppContext);
  const { APIService, currentUser } = globalContext;

  const submitTroiPreferences = React.useCallback(
    async (newValue: boolean) => {
      if (!currentUser?.auth_token) {
        toast.error("You must be logged in to update your preferences");
        return;
      }

      await APIService.submitTroiPreferences(currentUser.auth_token, newValue);
    },
    [APIService, currentUser?.auth_token]
  );

  const { triggerAutoSave } = useAutoSave<boolean>({
    delay: 3000,
    onSave: submitTroiPreferences,
  });

  return (
    <SelectTroiPreferences
      exportToSpotify={exportToSpotify}
      autoSave={triggerAutoSave}
    />
  );
}
