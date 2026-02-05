import * as React from "react";
import { union } from "lodash";
import {
  faSpotify,
  faApple,
  faSoundcloud,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { Helmet } from "react-helmet";
import { Link } from "react-router";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toast } from "react-toastify";
import ReactTooltip from "react-tooltip";
import { ReactSortable } from "react-sortablejs";
import { faGripLines } from "@fortawesome/free-solid-svg-icons";
import { IconDefinition, IconProp } from "@fortawesome/fontawesome-svg-core";
import Switch from "../../components/Switch";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SpotifyPlayer from "../../common/brainzplayer/SpotifyPlayer";
import SoundcloudPlayer from "../../common/brainzplayer/SoundcloudPlayer";
import FunkwhalePlayer from "../../common/brainzplayer/FunkwhalePlayer";
import { ToastMsg } from "../../notifications/Notifications";
import AppleMusicPlayer from "../../common/brainzplayer/AppleMusicPlayer";
import Card from "../../components/Card";
import faInternetArchive from "../../common/icons/faInternetArchive";
import faFunkwhale from "../../common/icons/faFunkwhale";
import { faNavidrome } from "../../common/icons/faNavidrome";
import useAutoSave from "../../hooks/useAutoSave";

export const dataSourcesInfo = {
  youtube: {
    name: "YouTube",
    icon: faYoutube,
    color: "#FF0000",
  },
  spotify: {
    name: "Spotify",
    icon: faSpotify,
    color: "#1DB954",
  },
  soundcloud: {
    name: "SoundCloud",
    icon: faSoundcloud,
    color: "#FF8800",
  },
  appleMusic: {
    name: "Apple Music",
    icon: faApple,
    color: "#000000",
  },
  internetArchive: {
    name: "Internet Archive",
    icon: faInternetArchive,
    color: "#6c757d",
  },
  funkwhale: {
    name: "Funkwhale",
    icon: faFunkwhale,
    color: "#009FE3",
  },
  navidrome: {
    name: "Navidrome",
    icon: faNavidrome,
    color: "#0084ff",
  },
} as const;

export type DataSourceKey = keyof typeof dataSourcesInfo;
type DataSourceInfo = typeof dataSourcesInfo[keyof typeof dataSourcesInfo];

export const defaultDataSourcesPriority = [
  "spotify",
  "appleMusic",
  "soundcloud",
  "funkwhale",
  "navidrome",
  "youtube",
  "internetArchive",
] as DataSourceKey[];

function BrainzPlayerSettings() {
  const {
    spotifyAuth,
    soundcloudAuth,
    appleAuth,
    funkwhaleAuth,
    navidromeAuth,
    APIService,
    currentUser,
    userPreferences,
  } = React.useContext(GlobalAppContext);

  // Use a single settings object
  // Avoids the stale  issues previously caused by reading independent usestate values
  // and simplifies autosave by always working with the latest snapshot.

  const [settings, setSettings] = React.useState<BrainzPlayerSettings>(() => ({
    youtubeEnabled: userPreferences?.brainzplayer?.youtubeEnabled ?? true,
    spotifyEnabled:
      userPreferences?.brainzplayer?.spotifyEnabled ??
      SpotifyPlayer.hasPermissions(spotifyAuth),
    soundcloudEnabled:
      userPreferences?.brainzplayer?.soundcloudEnabled ??
      SoundcloudPlayer.hasPermissions(soundcloudAuth),
    appleMusicEnabled:
      userPreferences?.brainzplayer?.appleMusicEnabled ??
      AppleMusicPlayer.hasPermissions(appleAuth),
    internetArchiveEnabled:
      userPreferences?.brainzplayer?.internetArchiveEnabled ?? true,
    funkwhaleEnabled:
      userPreferences?.brainzplayer?.funkwhaleEnabled ??
      FunkwhalePlayer.hasPermissions(funkwhaleAuth),
    navidromeEnabled:
      userPreferences?.brainzplayer?.navidromeEnabled ??
      Boolean(navidromeAuth?.instance_url),
    brainzplayerEnabled:
      userPreferences?.brainzplayer?.brainzplayerEnabled ?? true,
    dataSourcesPriority: union(
      userPreferences?.brainzplayer?.dataSourcesPriority ?? [],
      defaultDataSourcesPriority
    ),
  }));

  const getDataSourcesPriorityList = React.useCallback(() => {
    const sortedList = settings.dataSourcesPriority.map(
      (id: DataSourceKey) => ({
        id,
        info: dataSourcesInfo[id],
      })
    );

    return sortedList as {
      id: DataSourceKey;
      info: DataSourceInfo;
    }[];
  }, [settings.dataSourcesPriority]);

  const sortedList = getDataSourcesPriorityList();

  const saveSettings = React.useCallback(
    async (newSettings: BrainzPlayerSettings) => {
      if (!currentUser?.auth_token) {
        toast.error("You must be logged in to update your preferences");
        return;
      }

      await APIService.submitBrainzplayerPreferences(
        currentUser.auth_token,
        newSettings
      );

      // Update the global context values

      // eslint-disable-next-line react-hooks/exhaustive-deps
      if (userPreferences) {
        userPreferences.brainzplayer = newSettings;
      }
    },
    [APIService, currentUser?.auth_token, userPreferences]
  );

  const { triggerAutoSave } = useAutoSave<BrainzPlayerSettings>({
    delay: 3000,
    onSave: saveSettings,
  });
  // helper to update the next state from previous

  const updateSettings = React.useCallback(
    (updater: (prev: BrainzPlayerSettings) => BrainzPlayerSettings) => {
      setSettings((prev) => {
        const next = updater(prev);
        // Trigger autosave with the new next state
        triggerAutoSave(next);
        return next;
      });
    },
    [triggerAutoSave]
  );

  return (
    <>
      <Helmet>
        <title>BrainzPlayer Settings</title>
      </Helmet>
      <h2 className="page-title">BrainzPlayer settings</h2>
      <p className="border-start bg-light border-info border-3 px-3 py-2 mb-3 fs-4">
        Changes are saved automatically.
      </p>
      <Switch
        id="enable-brainzplayer"
        value="brainzplayer"
        checked={settings.brainzplayerEnabled}
        onChange={() =>
          updateSettings((prev) => ({
            ...prev,
            brainzplayerEnabled: !prev.brainzplayerEnabled,
          }))
        }
        switchLabel={
          <span
            className={`text-brand ${
              !settings.brainzplayerEnabled ? "text-muted" : ""
            }`}
          >
            <span>Enable the player</span>
          </span>
        }
      />
      <details open={settings.brainzplayerEnabled}>
        <summary>
          {!settings.brainzplayerEnabled && (
            <p className="text-primary">
              <b>You will not be able to play any music on Listenbrainz</b>
            </p>
          )}
        </summary>
        <h3 className="mt-4">Play music with...</h3>
        <p>Choose which music services to use for playback in ListenBrainz.</p>

        <p>
          YouTube is enabled by default. For a better listening experience we
          recommend enabling another service.
        </p>
        <div
          className="mb-4"
          data-tip
          data-tip-disable={
            settings.spotifyEnabled || SpotifyPlayer.hasPermissions(spotifyAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-spotify"
            disabled={
              !settings.spotifyEnabled &&
              !SpotifyPlayer.hasPermissions(spotifyAuth)
            }
            value="spotify"
            checked={settings.spotifyEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                spotifyEnabled: !prev.spotifyEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.spotifyEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faSpotify}
                    color={
                      settings.spotifyEnabled
                        ? dataSourcesInfo.spotify.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;Spotify</span>
              </span>
            }
          />
          <br />
          <small>
            Spotify requires a premium account.
            <br />
            Sign in on the{" "}
            <Link to="/settings/music-services/details/">
              &quot;connect services&quot; page
            </Link>
            .
          </small>
        </div>
        <div
          className="mb-4"
          data-tip
          data-tip-disable={
            settings.appleMusicEnabled ||
            AppleMusicPlayer.hasPermissions(appleAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-apple-music"
            value="apple-music"
            disabled={
              !settings.appleMusicEnabled &&
              !AppleMusicPlayer.hasPermissions(appleAuth)
            }
            checked={settings.appleMusicEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                appleMusicEnabled: !prev.appleMusicEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.appleMusicEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faApple}
                    color={
                      settings.appleMusicEnabled
                        ? dataSourcesInfo.appleMusic.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;Apple Music</span>
              </span>
            }
          />
          <br />
          <small>
            Apple Music requires a premium account.
            <br />
            Sign in on the{" "}
            <Link to="/settings/music-services/details/">
              &quot;connect services&quot; page
            </Link>
            . You will need to sign in every 6 months, as the authorization
            expires.
          </small>
        </div>
        <div
          className="mb-4"
          data-tip
          data-tip-disable={
            settings.soundcloudEnabled ||
            SoundcloudPlayer.hasPermissions(soundcloudAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-soundcloud"
            value="soundcloud"
            disabled={
              !settings.soundcloudEnabled &&
              !SoundcloudPlayer.hasPermissions(soundcloudAuth)
            }
            checked={settings.soundcloudEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                soundcloudEnabled: !prev.soundcloudEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.soundcloudEnabled ? "text-muted" : ""
                }`}
              >
                <span
                  className={settings.soundcloudEnabled ? "text-success" : ""}
                >
                  <FontAwesomeIcon
                    icon={faSoundcloud}
                    color={
                      settings.soundcloudEnabled
                        ? dataSourcesInfo.soundcloud.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;SoundCloud</span>
              </span>
            }
          />
          <br />
          <small>
            SoundCloud requires a free account.
            <br />
            Sign in on the{" "}
            <Link to="/settings/music-services/details/">
              &quot;connect services&quot; page
            </Link>
          </small>
        </div>
        <div
          className="mb-4"
          data-tip
          data-tip-disable={
            settings.funkwhaleEnabled ||
            FunkwhalePlayer.hasPermissions(funkwhaleAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-funkwhale"
            value="funkwhale"
            disabled={
              !settings.funkwhaleEnabled &&
              !FunkwhalePlayer.hasPermissions(funkwhaleAuth)
            }
            checked={settings.funkwhaleEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                funkwhaleEnabled: !prev.funkwhaleEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.funkwhaleEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faFunkwhale as IconProp}
                    color={
                      settings.funkwhaleEnabled
                        ? dataSourcesInfo.funkwhale.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;Funkwhale</span>
              </span>
            }
          />
          <br />
          <small>
            Funkwhale is a federated audio platform. You will need to connect a
            Funkwhale instance.
            <br />
            Sign in on the{" "}
            <Link to="/settings/music-services/details/">
              &quot;connect services&quot; page
            </Link>
          </small>
        </div>
        <div
          className="mb-4"
          data-tip
          data-tip-disable={
            settings.navidromeEnabled || Boolean(navidromeAuth?.instance_url)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-navidrome"
            value="navidrome"
            disabled={
              !settings.navidromeEnabled && !navidromeAuth?.instance_url
            }
            checked={settings.navidromeEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                navidromeEnabled: !prev.navidromeEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.navidromeEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faNavidrome as IconProp}
                    color={
                      settings.navidromeEnabled
                        ? dataSourcesInfo.navidrome.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;Navidrome</span>
              </span>
            }
          />
          <br />
          <small>
            Navidrome is a self-hosted music streaming server. You will need to
            connect a Navidrome instance.
            <br />
            Sign in on the{" "}
            <Link to="/settings/music-services/details/">
              &quot;connect services&quot; page
            </Link>
          </small>
        </div>
        <div className="mb-4">
          <Switch
            id="enable-youtube"
            value="youtube"
            checked={settings.youtubeEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                youtubeEnabled: !prev.youtubeEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.youtubeEnabled ? "text-muted" : ""
                }`}
              >
                <span className={settings.youtubeEnabled ? "text-success" : ""}>
                  <FontAwesomeIcon
                    icon={faYoutube}
                    color={
                      settings.youtubeEnabled
                        ? dataSourcesInfo.youtube.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;YouTube</span>
              </span>
            }
          />
          <br />
          <small>
            YouTube does not require an account and is the default fallback.
            Search results from YouTube are often inaccurate.
            <br />
            By using YouTube you agree to be bound by the YouTube Terms of
            Service:
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
        <div className="mb-4">
          <Switch
            id="enable-internet-archive"
            value="internetArchive"
            checked={settings.internetArchiveEnabled}
            onChange={() =>
              updateSettings((prev) => ({
                ...prev,
                internetArchiveEnabled: !prev.internetArchiveEnabled,
              }))
            }
            switchLabel={
              <span
                className={`text-brand ${
                  !settings.internetArchiveEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={dataSourcesInfo.internetArchive.icon}
                    color={
                      settings.internetArchiveEnabled
                        ? dataSourcesInfo.internetArchive.color
                        : ""
                    }
                  />
                </span>
                <span>&nbsp;Internet Archive</span>
              </span>
            }
          />
          <br />
          <small>
            Internet Archive is a free, public domain audio archive.
          </small>
        </div>
        <h3 className="mt-4">Music services priority</h3>
        <p>
          You have the option to adjust the priority of the music services. They
          will be used in the order you set here.
        </p>
        <p>Drag and drop the services to reorder them:</p>
        {/* Explicit moveDataSource handler is no longer required.
         ReactSortable  provides the updated order via setList */}

        <ReactSortable
          list={sortedList}
          setList={(newState) => {
            updateSettings((prev) => ({
              ...prev,
              dataSourcesPriority: newState.map(
                (item: { id: DataSourceKey }) => item.id
              ),
            }));
          }}
          handle=".drag-handle"
        >
          {sortedList.map((item) => (
            <Card
              key={item.id}
              className="listen-card playlist-item-card"
              style={{ maxWidth: "900px" }}
            >
              <div className="main-content text-brand">
                <span className="drag-handle text-muted">
                  <FontAwesomeIcon icon={faGripLines as IconProp} />
                </span>
                <span>
                  <FontAwesomeIcon
                    icon={item.info?.icon}
                    color={item.info?.color}
                  />
                </span>
                <span>&nbsp;{item.info?.name}</span>
              </div>
            </Card>
          ))}
        </ReactSortable>
      </details>
      <ReactTooltip id="login-first" aria-haspopup="true" delayHide={500}>
        You must login to this service in the &quot;Connect services&quot;
        section before using it.
      </ReactTooltip>
    </>
  );
}

export default BrainzPlayerSettings;
