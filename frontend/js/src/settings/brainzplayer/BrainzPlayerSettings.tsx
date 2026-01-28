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
import SaveStatusIndicator from "../../components/SaveStatusIndicator";

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
  const [appleMusicEnabled, setAppleMusicEnabled] = React.useState(
    userPreferences?.brainzplayer?.appleMusicEnabled ??
      AppleMusicPlayer.hasPermissions(appleAuth)
  );
  const [internetArchiveEnabled, setInternetArchiveEnabled] = React.useState(
    userPreferences?.brainzplayer?.internetArchiveEnabled ?? true
  );
  const [funkwhaleEnabled, setFunkwhaleEnabled] = React.useState(
    userPreferences?.brainzplayer?.funkwhaleEnabled ??
      FunkwhalePlayer.hasPermissions(funkwhaleAuth)
  );
  const [navidromeEnabled, setNavidromeEnabled] = React.useState(
    userPreferences?.brainzplayer?.navidromeEnabled ??
      Boolean(navidromeAuth?.instance_url)
  );
  const [brainzplayerEnabled, setBrainzplayerEnabled] = React.useState(
    userPreferences?.brainzplayer?.brainzplayerEnabled ?? true
  );

  // Combine saved priority list and default list to add any new music service at the end
  const [dataSourcesPriority, setDataSourcesPriority] = React.useState<
    DataSourceKey[]
  >(
    union(
      userPreferences?.brainzplayer?.dataSourcesPriority ?? [],
      defaultDataSourcesPriority
    )
  );
  const moveDataSource = (evt: any) => {
    const { newIndex, oldIndex } = evt;
    const newPriority = [...dataSourcesPriority];
    const [removed] = newPriority.splice(oldIndex, 1);
    newPriority.splice(newIndex, 0, removed);
    setDataSourcesPriority(newPriority);
  };

  const getDataSourcesPriorityList = React.useCallback(() => {
    const sortedList = dataSourcesPriority.map((id) => ({
      id,
      info: dataSourcesInfo[id],
    }));

    return sortedList as {
      id: DataSourceKey;
      info: DataSourceInfo;
    }[];
  }, [dataSourcesPriority]);

  const sortedList = getDataSourcesPriorityList();

  // Ref created To store current values

  const settingsRef = React.useRef({
    youtubeEnabled,
    spotifyEnabled,
    soundcloudEnabled,
    appleMusicEnabled,
    internetArchiveEnabled,
    funkwhaleEnabled,
    navidromeEnabled,
    brainzplayerEnabled,
    dataSourcesPriority,
  });

  // Update Refs whenever state changes due to setting changes
  React.useEffect(() => {
    settingsRef.current = {
      youtubeEnabled,
      spotifyEnabled,
      soundcloudEnabled,
      appleMusicEnabled,
      internetArchiveEnabled,
      funkwhaleEnabled,
      navidromeEnabled,
      brainzplayerEnabled,
      dataSourcesPriority,
    };
  }, [
    youtubeEnabled,
    spotifyEnabled,
    soundcloudEnabled,
    appleMusicEnabled,
    internetArchiveEnabled,
    funkwhaleEnabled,
    navidromeEnabled,
    brainzplayerEnabled,
    dataSourcesPriority,
  ]);
  const saveSettings = React.useCallback(async () => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your preferences");
      return;
    }

    // Get CURRENT values from ref, not captured values
    const currentSettings = settingsRef.current;
    const { submitBrainzplayerPreferences } = APIService;
    try {
      await submitBrainzplayerPreferences(
        currentUser.auth_token,
        currentSettings
      );

      toast.success("Saved your preferences successfully");
      // Update the global context values

      // eslint-disable-next-line react-hooks/exhaustive-deps
      if (userPreferences) {
        userPreferences.brainzplayer = currentSettings;
      }
      // console.log("WARNING: userPreferences is undefined!");
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
  }, [APIService, currentUser?.auth_token, userPreferences]);

  const {
    triggerAutoSave,
    cancelAutoSave,
    saveStatus,
    errorMessage,
  } = useAutoSave({
    delay: 1000,
    onSave: saveSettings,
  });

  // TO skip the auto save during initial render of screen before
  // user make change . effectRuns

  // Skip initial hydration passes
  const effectRuns = React.useRef(0);

  React.useEffect(() => {
    effectRuns.current += 1;

    // Skip the first two runs (initial mount + hydration updates) which are not
    // caused by user
    if (effectRuns.current <= 2) {
      return;
    }

    // now the change which occur will be made by user
    triggerAutoSave();
  }, [
    youtubeEnabled,
    spotifyEnabled,
    soundcloudEnabled,
    appleMusicEnabled,
    internetArchiveEnabled,
    funkwhaleEnabled,
    navidromeEnabled,
    brainzplayerEnabled,
    dataSourcesPriority,
    triggerAutoSave,
  ]);
  // Adding  manual save function
  const handleManualSave = async () => {
    cancelAutoSave(); // Cancelling any pending auto-save
    await saveSettings();
  };

  return (
    <>
      <Helmet>
        <title>BrainzPlayer Settings</title>
      </Helmet>
      <h2 className="page-title">BrainzPlayer settings</h2>
      <Switch
        id="enable-brainzplayer"
        value="brainzplayer"
        checked={brainzplayerEnabled}
        onChange={(e) => setBrainzplayerEnabled(!brainzplayerEnabled)}
        switchLabel={
          <span
            className={`text-brand ${!brainzplayerEnabled ? "text-muted" : ""}`}
          >
            <span>Enable the player</span>
          </span>
        }
      />
      <details open={brainzplayerEnabled}>
        <summary>
          {!brainzplayerEnabled && (
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
            spotifyEnabled || SpotifyPlayer.hasPermissions(spotifyAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-spotify"
            disabled={
              !spotifyEnabled && !SpotifyPlayer.hasPermissions(spotifyAuth)
            }
            value="spotify"
            checked={spotifyEnabled}
            onChange={(e) => setSpotifyEnabled(!spotifyEnabled)}
            switchLabel={
              <span
                className={`text-brand ${!spotifyEnabled ? "text-muted" : ""}`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faSpotify}
                    color={spotifyEnabled ? dataSourcesInfo.spotify.color : ""}
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
            appleMusicEnabled || AppleMusicPlayer.hasPermissions(appleAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-apple-music"
            value="apple-music"
            disabled={
              !appleMusicEnabled && !AppleMusicPlayer.hasPermissions(appleAuth)
            }
            checked={appleMusicEnabled}
            onChange={(e) => setAppleMusicEnabled(!appleMusicEnabled)}
            switchLabel={
              <span
                className={`text-brand ${
                  !appleMusicEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faApple}
                    color={
                      appleMusicEnabled ? dataSourcesInfo.appleMusic.color : ""
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
            soundcloudEnabled || SoundcloudPlayer.hasPermissions(soundcloudAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-soundcloud"
            value="soundcloud"
            disabled={
              !soundcloudEnabled &&
              !SoundcloudPlayer.hasPermissions(soundcloudAuth)
            }
            checked={soundcloudEnabled}
            onChange={(e) => setSoundcloudEnabled(!soundcloudEnabled)}
            switchLabel={
              <span
                className={`text-brand ${
                  !soundcloudEnabled ? "text-muted" : ""
                }`}
              >
                <span className={soundcloudEnabled ? "text-success" : ""}>
                  <FontAwesomeIcon
                    icon={faSoundcloud}
                    color={
                      soundcloudEnabled ? dataSourcesInfo.soundcloud.color : ""
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
            funkwhaleEnabled || FunkwhalePlayer.hasPermissions(funkwhaleAuth)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-funkwhale"
            value="funkwhale"
            disabled={
              !funkwhaleEnabled &&
              !FunkwhalePlayer.hasPermissions(funkwhaleAuth)
            }
            checked={funkwhaleEnabled}
            onChange={(e) => setFunkwhaleEnabled(!funkwhaleEnabled)}
            switchLabel={
              <span
                className={`text-brand ${
                  !funkwhaleEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faFunkwhale as IconProp}
                    color={
                      funkwhaleEnabled ? dataSourcesInfo.funkwhale.color : ""
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
            navidromeEnabled || Boolean(navidromeAuth?.instance_url)
          }
          data-for="login-first"
        >
          <Switch
            id="enable-navidrome"
            value="navidrome"
            disabled={!navidromeEnabled && !navidromeAuth?.instance_url}
            checked={navidromeEnabled}
            onChange={(e) => setNavidromeEnabled(!navidromeEnabled)}
            switchLabel={
              <span
                className={`text-brand ${
                  !navidromeEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={faNavidrome as IconProp}
                    color={
                      navidromeEnabled ? dataSourcesInfo.navidrome.color : ""
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
            checked={youtubeEnabled}
            onChange={(e) => setYoutubeEnabled(!youtubeEnabled)}
            switchLabel={
              <span
                className={`text-brand ${!youtubeEnabled ? "text-muted" : ""}`}
              >
                <span className={youtubeEnabled ? "text-success" : ""}>
                  <FontAwesomeIcon
                    icon={faYoutube}
                    color={youtubeEnabled ? dataSourcesInfo.youtube.color : ""}
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
            checked={internetArchiveEnabled}
            onChange={(e) => setInternetArchiveEnabled(!internetArchiveEnabled)}
            switchLabel={
              <span
                className={`text-brand ${
                  !internetArchiveEnabled ? "text-muted" : ""
                }`}
              >
                <span>
                  <FontAwesomeIcon
                    icon={dataSourcesInfo.internetArchive.icon}
                    color={
                      internetArchiveEnabled
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
        <ReactSortable
          list={sortedList}
          setList={(newState) => {
            setDataSourcesPriority(newState.map((item) => item.id));
          }}
          onEnd={moveDataSource}
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
      <div className="mt-3">
        <SaveStatusIndicator status={saveStatus} errorMessage={errorMessage} />
      </div>
      <button
        className="btn btn-lg btn-info"
        type="button"
        onClick={handleManualSave}
      >
        Save BrainzPlayer settings
      </button>
      <ReactTooltip id="login-first" aria-haspopup="true" delayHide={500}>
        You must login to this service in the &quot;Connect services&quot;
        section before using it.
      </ReactTooltip>
    </>
  );
}

export default BrainzPlayerSettings;
