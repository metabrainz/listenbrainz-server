import * as React from "react";
import {
  faSpotify,
  faApple,
  faSoundcloud,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { Helmet } from "react-helmet";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import Switch from "../../components/Switch";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SpotifyPlayer from "../../common/brainzplayer/SpotifyPlayer";
import SoundcloudPlayer from "../../common/brainzplayer/SoundcloudPlayer";
import { ToastMsg } from "../../notifications/Notifications";

function BrainzPlayerSettings() {
  const {
    spotifyAuth,
    soundcloudAuth,
    userPreferences,
    APIService,
    currentUser,
  } = React.useContext(GlobalAppContext);
  const [youtubeEnabled, setYoutubeEnabled] = React.useState(
    userPreferences?.brainzplayer?.youtubeEnabled ?? true
  );
  const [spotifyEnabled, setSpotifyEnabled] = React.useState(
    userPreferences?.brainzplayer?.spotifyEnabled ??
      SpotifyPlayer.hasPermissions(spotifyAuth)
  );
  const [soundcloudEnabled, setSoundcloudEnabled] = React.useState(
    userPreferences?.brainzplayer?.soundcloudEnabled ??
      SoundcloudPlayer.hasPermissions(soundcloudAuth)
  );

  const saveSettings = React.useCallback(async () => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your preferences");
      return;
    }
    const { submitBrainzplayerPreferences } = APIService;
    try {
      await submitBrainzplayerPreferences(currentUser.auth_token, {
        youtubeEnabled,
        spotifyEnabled,
        soundcloudEnabled,
      });
      toast.success("Saved your preferences successfully");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error saving preferences"
          message={
            <>
              {error.toString()}
              <br />
              Please try again or contact us if the issue persists.
            </>
          }
        />
      );
    }
  }, [
    youtubeEnabled,
    spotifyEnabled,
    soundcloudEnabled,
    APIService,
    currentUser?.auth_token,
  ]);

  return (
    <>
      <Helmet>
        <title>BrainzPlayer Settings</title>
      </Helmet>
      <h2 className="page-title">BrainzPlayer Settings</h2>
      <h4 className="page-title">Music Players</h4>
      <p>
        You can choose which music services to play music from on listenBrainz.
        To sign in and authorize your account please go to the{" "}
        <Link to="/settings/music-services/">music services page</Link>. <br />
        If you don&apos;t have a subscription to a music service listed below,
        Youtube will be used by default as it does not require an account.
        However the search results from Youtube are often inaccurate, and for a
        better listening experience we recommend one of the other services (if
        you have one available).
      </p>
      <p>
        <Switch
          id="enable-spotify"
          disabled={!SpotifyPlayer.hasPermissions(spotifyAuth)}
          value="spotify"
          checked={spotifyEnabled}
          onChange={(e) => setSpotifyEnabled(!spotifyEnabled)}
          switchLabel={
            <span
              className={`text-brand ${spotifyEnabled ? "text-success" : ""}`}
            >
              <FontAwesomeIcon icon={faSpotify} />
              &nbsp;Spotify
            </span>
          }
        />
        <br />
        <small>
          Spotify requires a premium account to play full songs on third-party
          websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/">music services page</Link>.
        </small>
      </p>
      {/* <p>
        <Switch
          id="enable-apple-music"
          value="apple-music"
          disabled={!AppleMusicPlayer.hasPermissions(appleAuth)}
          checked={appleMusicEnabled}
          onChange={(e) => setAppleMusicEnabled(!appleMusicEnabled)}
          switchLabel={
            <span className={`text-brand ${enabled ? "text-success":""}`}>
              <FontAwesomeIcon icon={faApple} />
              &nbsp;Apple Music Player
            </span>
          }
        />
        <br/>
        <small>
          Apple Music requires a premium account to play full songs on
          third-party websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/">music services page</Link>. You
          will need to sign in every 6 months.
        </small>
      </p> */}
      <p>
        <Switch
          id="enable-soundcloud"
          value="soundcloud"
          disabled={!SoundcloudPlayer.hasPermissions(soundcloudAuth)}
          checked={soundcloudEnabled}
          onChange={(e) => setSoundcloudEnabled(!soundcloudEnabled)}
          switchLabel={
            <span
              className={`text-brand ${
                soundcloudEnabled ? "text-success" : ""
              }`}
            >
              <FontAwesomeIcon icon={faSoundcloud} />
              &nbsp;Soundcloud
            </span>
          }
        />
        <br />
        <small>
          Soundcloud requires a free account to play full songs on third-party
          websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/">music services page</Link>
        </small>
      </p>
      <p>
        <Switch
          id="enable-youtube"
          value="youtube"
          checked={youtubeEnabled}
          onChange={(e) => setYoutubeEnabled(!youtubeEnabled)}
          switchLabel={
            <span
              className={`text-brand ${youtubeEnabled ? "text-success" : ""}`}
            >
              <FontAwesomeIcon icon={faYoutube} />
              &nbsp;Youtube
            </span>
          }
        />
        <br />
        <small>
          Youtube does not require signing in and provides a good fallback. Be
          aware the search results from Youtube are often inaccurate.
          <br />
          By using Youtube to play music, you agree to be bound by the YouTube
          Terms of Service. See their terms of service and privacy policy below:
          <ul>
            <li>
              <a
                href="https://www.youtube.com/t/terms"
                target="_blank"
                rel="noreferrer"
              >
                Youtube Terms of Service
              </a>
            </li>
            <li>
              <a
                href="https://policies.google.com/privacy"
                target="_blank"
                rel="noreferrer"
              >
                Google Privacy Policy
              </a>
            </li>
          </ul>
        </small>
      </p>
      <br />
      <button
        className="btn btn-lg btn-info"
        type="button"
        onClick={saveSettings}
      >
        Save preferences
      </button>
    </>
  );
}

export default BrainzPlayerSettings;
