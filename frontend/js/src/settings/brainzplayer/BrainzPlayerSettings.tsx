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
import ReactTooltip from "react-tooltip";
import Switch from "../../components/Switch";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SpotifyPlayer from "../../common/brainzplayer/SpotifyPlayer";
import SoundcloudPlayer from "../../common/brainzplayer/SoundcloudPlayer";
import { ToastMsg } from "../../notifications/Notifications";

function BrainzPlayerSettings() {
  const {
    spotifyAuth,
    soundcloudAuth,
    APIService,
    currentUser,
  } = React.useContext(GlobalAppContext);
  const { userPreferences } = React.useContext(GlobalAppContext);
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
      // Update the global context values

      // eslint-disable-next-line react-hooks/exhaustive-deps
      if (userPreferences) {
        userPreferences.brainzplayer = {
          ...userPreferences?.brainzplayer,
          youtubeEnabled,
          spotifyEnabled,
          soundcloudEnabled,
        };
      }
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
    userPreferences,
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
        <Link to="/settings/music-services/details/">
          &quot;connect services&quot; page
        </Link>
        . <br />
        If you don&apos;t have a subscription to a music service listed below,
        Youtube will be used by default as it does not require an account.
        However the search results from Youtube are often inaccurate, and for a
        better listening experience we recommend one of the other services (if
        you have one available).
      </p>
      <div
        className="mb-15"
        data-tip={!SpotifyPlayer.hasPermissions(spotifyAuth)}
        data-for="login-first"
      >
        <Switch
          id="enable-spotify"
          disabled={!SpotifyPlayer.hasPermissions(spotifyAuth)}
          value="spotify"
          checked={spotifyEnabled}
          onChange={(e) => setSpotifyEnabled(!spotifyEnabled)}
          switchLabel={
            <span
              className={`text-brand ${!spotifyEnabled ? "text-muted" : ""}`}
            >
              <span className={spotifyEnabled ? "text-success" : ""}>
                <FontAwesomeIcon icon={faSpotify} />
              </span>
              <span>&nbsp;Spotify</span>
            </span>
          }
        />
        <br />
        <small>
          Spotify requires a premium account to play full songs on third-party
          websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/details/">
            &quot;connect services&quot; page
          </Link>
          .
        </small>
      </div>
      {/* <div className="mb-15"
          data-tip={!AppleMusicPlayer.hasPermissions(appleAuth)}
          data-for="login-first">
        <Switch
          id="enable-apple-music"
          value="apple-music"
          disabled={!AppleMusicPlayer.hasPermissions(appleAuth)}
          checked={appleMusicEnabled}
          
          onChange={(e) => setAppleMusicEnabled(!appleMusicEnabled)}
          switchLabel={
            <span
              className={`text-brand ${!appleMusicEnabled ? "text-muted" : ""}`}
            >
              <span className={appleMusicEnabled ? "text-success" : ""}>
                <FontAwesomeIcon icon={faApple} />
              </span>
              <span>&nbsp;Apple Music</span>
            </span>
          }
        />
        <br/>
        <small>
          Apple Music requires a premium account to play full songs on
          third-party websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/details/">&quot;connect services&quot; page</Link>. You
          will need to sign in every 6 months.
        </small>
      </div> */}
      <div
        className="mb-15"
        data-tip={!SoundcloudPlayer.hasPermissions(soundcloudAuth)}
        data-for="login-first"
      >
        <Switch
          id="enable-soundcloud"
          value="soundcloud"
          disabled={!SoundcloudPlayer.hasPermissions(soundcloudAuth)}
          checked={soundcloudEnabled}
          onChange={(e) => setSoundcloudEnabled(!soundcloudEnabled)}
          switchLabel={
            <span
              className={`text-brand ${!soundcloudEnabled ? "text-muted" : ""}`}
            >
              <span className={soundcloudEnabled ? "text-success" : ""}>
                <FontAwesomeIcon icon={faSoundcloud} />
              </span>
              <span>&nbsp;Soundcloud</span>
            </span>
          }
        />
        <br />
        <small>
          Soundcloud requires a free account to play full songs on third-party
          websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/details/">
            &quot;connect services&quot; page
          </Link>
        </small>
      </div>
      <div className="mb-15">
        <Switch
          id="enable-youtube"
          value="youtube"
          checked={youtubeEnabled}
          onChange={(e) => setYoutubeEnabled(!youtubeEnabled)}
          switchLabel={
            <span
              className={`text-brand ${!youtubeEnabled ? "text-muted" : ""}`}
            >
              <span className={youtubeEnabled ? "text-success" : ""}>
                <FontAwesomeIcon icon={faYoutube} />
              </span>
              <span>&nbsp;Youtube</span>
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
      </div>
      <br />
      <button
        className="btn btn-lg btn-info"
        type="button"
        onClick={saveSettings}
      >
        Save preferences
      </button>
      <ReactTooltip id="login-first" aria-haspopup="true" delayHide={500}>
        You must login to this service in the &quot;Connect services&quot;
        section before using it.
      </ReactTooltip>
    </>
  );
}

export default BrainzPlayerSettings;
