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
import Switch from "../../components/Switch";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SpotifyPlayer from "../../common/brainzplayer/SpotifyPlayer";
import AppleMusicPlayer from "../../common/brainzplayer/AppleMusicPlayer";
import SoundcloudPlayer from "../../common/brainzplayer/SoundcloudPlayer";

function BrainzPlayerSettings() {
  const { appleAuth, spotifyAuth, soundcloudAuth } = React.useContext(
    GlobalAppContext
  );
  const [youtubeEnabled, setYoutubeEnabled] = React.useState(true);
  const [appleMusicEnabled, setAppleMusicEnabled] = React.useState(
    Boolean(appleAuth?.music_user_token)
  );
  const [spotifyEnabled, setSpotifyEnabled] = React.useState(
    SpotifyPlayer.hasPermissions(spotifyAuth)
  );
  const [soundcloudEnabled, setSoundcloudEnabled] = React.useState(
    Boolean(soundcloudAuth?.access_token)
  );

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
            <>
              <FontAwesomeIcon icon={faSpotify} />
              Spotify Player
            </>
          }
        />
        <small>
          Spotify requires a premium account to play full songs on third-party
          websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/">music services page</Link>.
        </small>
      </p>
      <p>
        <Switch
          id="enable-apple-music"
          value="apple-music"
          disabled={!AppleMusicPlayer.hasPermissions(appleAuth)}
          checked={appleMusicEnabled}
          onChange={(e) => setAppleMusicEnabled(!appleMusicEnabled)}
          switchLabel={
            <>
              <FontAwesomeIcon icon={faApple} />
              Apple Music Player
            </>
          }
        />
        <small>
          Apple Music requires a premium account to play full songs on
          third-party websites. To sign in, please go to the{" "}
          <Link to="/settings/music-services/">music services page</Link>. You
          will need to sign in every 6 months.
        </small>
      </p>
      <p>
        <Switch
          id="enable-soundcloud"
          value="soundcloud"
          disabled={!SoundcloudPlayer.hasPermissions(soundcloudAuth)}
          checked={soundcloudEnabled}
          onChange={(e) => setSoundcloudEnabled(!soundcloudEnabled)}
          switchLabel={
            <>
              <FontAwesomeIcon icon={faSoundcloud} />
              Soundcloud Player
            </>
          }
        />
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
            <>
              <FontAwesomeIcon icon={faYoutube} />
              Youtube Player
            </>
          }
        />
        <small>
          Youtube player does not require signing in and provides a good
          fallback. Be aware the search results from Youtube are often
          inaccurate.
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
    </>
  );
}

export default BrainzPlayerSettings;
