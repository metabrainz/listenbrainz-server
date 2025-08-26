import * as React from "react";

import { capitalize } from "lodash";
import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../../notifications/Notifications";
import ServicePermissionButton from "./components/ExternalServiceButton";
import LFMMusicServicePermissions from "./components/LFMMusicServicePermissions";
import {
  authorizeWithAppleMusic,
  loadAppleMusicKit,
  setupAppleMusicKit,
} from "../../../common/brainzplayer/AppleMusicPlayer";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type MusicServicesLoaderData = {
  current_spotify_permissions: string;
  current_critiquebrainz_permissions: string;
  current_soundcloud_permissions: string;
  current_apple_permissions: string;
  current_lastfm_permissions: string;
  current_funkwhale_permission: string;
  current_navidrome_permissions: string;
  current_lastfm_settings?: {
    external_user_id?: string;
    latest_listened_at?: string;
  };
  current_librefm_permissions: string;
  current_librefm_settings?: {
    external_user_id?: string;
    latest_listened_at?: string;
  };
  current_navidrome_settings?: {
    instance_url?: string;
    username?: string;
  };
};

export default function MusicServices() {
  const {
    spotifyAuth,
    soundcloudAuth,
    critiquebrainzAuth,
    currentUser,
    funkwhaleAuth,
    navidromeAuth,
  } = React.useContext(GlobalAppContext);

  const loaderData = useLoaderData() as MusicServicesLoaderData;

  const { appleAuth } = React.useContext(GlobalAppContext);

  const [permissions, setPermissions] = React.useState({
    spotify: loaderData.current_spotify_permissions,
    critiquebrainz: loaderData.current_critiquebrainz_permissions,
    soundcloud: loaderData.current_soundcloud_permissions,
    appleMusic: loaderData.current_apple_permissions,
    lastfm: loaderData.current_lastfm_permissions,
    funkwhale: loaderData.current_funkwhale_permission,
    navidrome: loaderData.current_navidrome_permissions,
    librefm: loaderData.current_librefm_permissions,
  });

  const [navidromeIsEditing, setNavidromeIsEditing] = React.useState(false);
  const [navidromeEditValues, setNavidromeEditValues] = React.useState({
    hostUrl: navidromeAuth?.instance_url || "",
    username: navidromeAuth?.username || "",
  });

  const navidromeEditButtonClass =
    permissions.navidrome !== "listen"
      ? "btn-default"
      : (navidromeIsEditing && "btn-success") || "btn-warning";
  const handlePermissionChange = async (
    serviceName: string,
    newValue: string
  ) => {
    try {
      const fetchUrl = `/settings/music-services/${serviceName}/disconnect/`;
      let fetchBody;
      const fetchHeaders: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (serviceName === "funkwhale" && newValue === "disable") {
        fetchBody = undefined;
        fetchHeaders.Authorization = `Token ${currentUser?.auth_token}`;
      } else if (serviceName === "navidrome" && newValue === "disable") {
        fetchBody = undefined;
        fetchHeaders.Authorization = `Token ${currentUser?.auth_token}`;
      } else {
        fetchBody = JSON.stringify({ action: newValue });
      }

      const response = await fetch(fetchUrl, {
        method: "POST",
        body: fetchBody,
        headers: fetchHeaders,
      });

      if (newValue === "disable") {
        toast.success(
          <ToastMsg
            title="Success"
            message={`${capitalize(
              serviceName
            )} integration has been disabled.`}
          />
        );

        setPermissions((prevState) => ({
          ...prevState,
          [serviceName]: newValue,
        }));
        switch (serviceName) {
          case "spotify":
            if (spotifyAuth) {
              spotifyAuth.access_token = undefined;
              spotifyAuth.permission = [];
            }
            break;
          case "soundcloud":
            if (soundcloudAuth) soundcloudAuth.access_token = undefined;
            break;
          case "critiquebrainz":
            if (critiquebrainzAuth) critiquebrainzAuth.access_token = undefined;
            break;
          // lastfm and librefm state is now managed in the LFMMusicServicePermissions component
          case "funkwhale":
            if (funkwhaleAuth) {
              funkwhaleAuth.access_token = undefined;
            }
            break;
          case "navidrome":
            if (navidromeAuth) {
              navidromeAuth.md5_auth_token = undefined;
              navidromeAuth.salt = undefined;
            }
            break;
          default:
            break;
        }
        return;
      }

      const data = await response.json();
      const { url } = data;

      window.location.href = url;
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to change permissions for ${capitalize(
            serviceName
          )}`}
        />
      );
    }
  };

  const handleAppleMusicPermissionChange = async (
    serviceName: string,
    action: string
  ) => {
    try {
      await loadAppleMusicKit();
      const musicKitInstance = await setupAppleMusicKit(
        appleAuth?.developer_token
      );
      // Delete or recreate the user in the database for this external service
      const response = await fetch(
        `/settings/music-services/apple/disconnect/`,
        {
          method: "POST",
          body: JSON.stringify({ action }),
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      if (action === "disable") {
        await musicKitInstance.unauthorize();
        (appleAuth as AppleMusicUser).music_user_token = undefined;
        toast.success(
          <ToastMsg
            title="Success"
            message="Apple Music integration has been disabled."
          />
        );
      } else {
        // authorizeWithAppleMusic also sends the token to the server
        const newToken = await authorizeWithAppleMusic(musicKitInstance);
        if (newToken) {
          // We know appleAuth is not undefined because we needed the developer_token
          // it contains in order to authorize the user successfully
          (appleAuth as AppleMusicUser).music_user_token = newToken;
        }
        toast.success(
          <ToastMsg
            title="Success"
            message="You are now logged in to Apple Music."
          />
        );
      }

      setPermissions((prevState) => ({
        ...prevState,
        appleMusic: action,
      }));
    } catch (error) {
      console.debug(error);
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to change permissions for Apple Music:${error.toString()}`}
        />
      );
    }
  };

  // Last.FM and Libre.FM connection handling is now managed in c

  const handleFunkwhaleConnect = async (
    evt: React.FormEvent<HTMLFormElement>
  ) => {
    evt.preventDefault();
    try {
      const formData = new FormData(evt.currentTarget);
      const hostUrl = formData.get("funkwhaleHostUrl") as string;

      if (!hostUrl) {
        throw Error("Funkwhale server URL is required");
      }

      const response = await fetch(
        `/settings/music-services/funkwhale/connect/`,
        {
          method: "POST",
          body: JSON.stringify({
            host_url: hostUrl,
          }),
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${currentUser?.auth_token}`,
          },
        }
      );

      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        throw Error("Server returned non-JSON response");
      }

      if (response.ok) {
        if (data.url) {
          // Store host URL in global context before redirect
          if (funkwhaleAuth) {
            funkwhaleAuth.instance_url = hostUrl;
          }
          // Redirect to Funkwhale authorization page
          window.location.href = data.url;
        } else {
          throw Error("No authorization URL received from server");
        }
      } else if (data?.error) {
        throw Error(data.error);
      } else {
        throw Error(`Server error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error("Funkwhale connection error:", error);
      toast.error(
        <ToastMsg
          title="Failed to connect to Funkwhale"
          message={error.toString()}
        />
      );
    }
  };

  const handleNavidromeConnect = async (
    evt: React.FormEvent<HTMLFormElement>
  ) => {
    evt.preventDefault();
    try {
      const formData = new FormData(evt.currentTarget);
      const hostUrl = formData.get("navidromeHostUrl") as string;
      const username = formData.get("navidromeUsername") as string;
      const password = formData.get("navidromePassword") as string;

      if (!hostUrl || !username || !password) {
        throw Error(
          "Navidrome server URL, username, and password are required"
        );
      }

      // If we're in edit mode and already connected, disconnect first to avoid duplicates
      if (navidromeIsEditing && permissions.navidrome === "listen") {
        try {
          const disconnectResponse = await fetch(
            `/settings/music-services/navidrome/disconnect/`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Token ${currentUser?.auth_token}`,
              },
            }
          );
        } catch (disconnectError) {
          // eslint-disable-next-line no-console
          console.warn(
            "Failed to disconnect before reconnecting:",
            disconnectError
          );
        }
      }

      const response = await fetch(
        `/settings/music-services/navidrome/connect/`,
        {
          method: "POST",
          body: JSON.stringify({
            host_url: hostUrl,
            username,
            password,
          }),
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${currentUser?.auth_token}`,
          },
        }
      );

      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        throw Error("Server returned non-JSON response");
      }

      if (response.ok) {
        if (navidromeAuth) {
          navidromeAuth.instance_url = hostUrl;
          navidromeAuth.username = username;
        }

        // Update edit values state
        setNavidromeEditValues({
          hostUrl,
          username,
        });

        // Exit edit mode if we were editing
        setNavidromeIsEditing(false);

        toast.success(
          <ToastMsg
            title="Success"
            message="Successfully connected to Navidrome!"
          />
        );
        setPermissions((prev) => ({ ...prev, navidrome: "listen" }));
      } else if (data?.error) {
        throw Error(data.error);
      } else {
        throw Error(`Server error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Failed to connect to Navidrome"
          message={error.toString()}
        />
      );
    }
  };

  const handleNavidromeEditToggle = () => {
    if (navidromeIsEditing) {
      // If we're saving, submit the form
      const form = document.getElementById("navidrome-form") as HTMLFormElement;
      if (form) {
        form.requestSubmit();
      }
    } else {
      // Start editing
      setNavidromeIsEditing(true);
    }
  };

  React.useEffect(() => {
    setNavidromeEditValues({
      hostUrl: navidromeAuth?.instance_url || "",
      username: navidromeAuth?.username || "",
    });
  }, [navidromeAuth?.instance_url, navidromeAuth?.username]);

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const funkwhaleError = params.get("error");
    const funkwhaleSuccess = params.get("success");
    const navidromeError = params.get("navidrome_error");
    const navidromeSuccess = params.get("navidrome_success");

    if (funkwhaleSuccess === "Successfully connected to Funkwhale") {
      toast.success(
        <ToastMsg
          title="Success"
          message="Successfully connected to Funkwhale!"
        />
      );
      setPermissions((prev) => ({ ...prev, funkwhale: "listen" }));
    } else if (funkwhaleError) {
      toast.error(
        <ToastMsg
          title="Funkwhale Connection Error"
          message={decodeURIComponent(funkwhaleError)}
        />
      );
    }

    if (navidromeSuccess === "Successfully connected to Navidrome") {
      toast.success(
        <ToastMsg
          title="Success"
          message="Successfully connected to Navidrome!"
        />
      );
      setPermissions((prev) => ({ ...prev, navidrome: "listen" }));
    } else if (navidromeError) {
      toast.error(
        <ToastMsg
          title="Navidrome Connection Error"
          message={decodeURIComponent(navidromeError)}
        />
      );
    }

    // Clear the query parameters from the URL for both success and error cases
    if (
      funkwhaleSuccess ||
      funkwhaleError ||
      navidromeSuccess ||
      navidromeError
    ) {
      window.history.replaceState(
        {},
        document.title,
        window.location.pathname + window.location.hash
      );
    }
  }, [funkwhaleAuth?.instance_url, navidromeAuth?.instance_url]);

  return (
    <>
      <Helmet>
        <title>External Music Services</title>
      </Helmet>
      <div id="user-profile">
        <h2 className="page-title">Connect third-party music services</h2>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Spotify</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your Spotify account to read your listening history,
              play music on ListenBrainz (requires Spotify Premium), or both.
              <br />
              <small>
                Full length playback requires Spotify Premium.
                <br />
                To play music, your browser must allow autoplaying media on
                listenbrainz.org.
                <br />
                If you encounter issues, try disconnecting and reconnecting your
                Spotify account and select the permissions to &apos;record
                listens and play music&apos; or &apos;play music only&apos;.
              </small>
            </p>
            <br />
            <div className="music-service-selection">
              <form onSubmit={(e) => e.preventDefault}>
                <ServicePermissionButton
                  service="spotify"
                  current={permissions.spotify}
                  value="both"
                  title="Activate both features (recommended)"
                  details="Permanently record your listening history and make it available for others to view and explore. Discover and play songs on ListenBrainz, and import/export playlists to and from Spotify."
                  handlePermissionChange={handlePermissionChange}
                />
                <ServicePermissionButton
                  service="spotify"
                  current={permissions.spotify}
                  value="listen"
                  title="Play music on ListenBrainz"
                  details="Discover and play songs on ListenBrainz, and import/export playlists to and from Spotify."
                  handlePermissionChange={handlePermissionChange}
                />
                <ServicePermissionButton
                  service="spotify"
                  current={permissions.spotify}
                  value="import"
                  title="Record listening history"
                  details="Record your listening history permanently and make it available for others to view and explore."
                  handlePermissionChange={handlePermissionChange}
                />
                <ServicePermissionButton
                  service="spotify"
                  current={permissions.spotify}
                  value="disable"
                  title="Disable"
                  details="You won't be able to listen to music on ListenBrainz or import listens using Spotify."
                  handlePermissionChange={handlePermissionChange}
                />
              </form>
            </div>

            <h3>A note about Spotify permissions</h3>

            <p>
              To record your listens you will need to grant permission to view
              your recent listens and your current listen.
            </p>

            <p>
              To play music on the ListenBrainz pages you will need to grant the
              permission to play streams from your account and create playlists.
              Spotify also requires permission to read your email address, your
              private information and your birthdate, to determine if you are a
              premium user -{" "}
              <b>ListenBrainz will never read these pieces of data</b>. Please
              feel free to{" "}
              <a
                href="https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/listens_importer/spotify.py"
                target="_blank"
                rel="noreferrer"
              >
                inspect our source code
              </a>{" "}
              any time!
            </p>

            <p>
              Revoke these permissions any time by disabling your Spotify
              connection.
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">CritiqueBrainz</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your CritiqueBrainz account to publish reviews directly
              from ListenBrainz. Reviews are public on ListenBrainz and
              CritiqueBrainz. To view or delete your reviews, visit your
              <a href="https://critiquebrainz.org/">CritiqueBrainz profile.</a>
            </p>
            <br />
            <div className="music-service-selection">
              <form>
                <ServicePermissionButton
                  service="critiquebrainz"
                  current={permissions.critiquebrainz}
                  value="review"
                  title="Publish reviews for your listens"
                  details="Publish reviews from ListenBrainz."
                  handlePermissionChange={handlePermissionChange}
                />
                <ServicePermissionButton
                  service="critiquebrainz"
                  current={permissions.critiquebrainz}
                  value="disable"
                  title="Disable"
                  details="You will not be able to publish reviews from ListenBrainz."
                  handlePermissionChange={handlePermissionChange}
                />
              </form>
            </div>
          </div>
        </div>

        <LFMMusicServicePermissions
          serviceName="lastfm"
          serviceDisplayName="Last.FM"
          existingPermissions={permissions.lastfm}
          externalUserId={loaderData.current_lastfm_settings?.external_user_id}
          existingLatestListenedAt={
            loaderData.current_lastfm_settings?.latest_listened_at
          }
          canImportFeedback
        />

        <LFMMusicServicePermissions
          serviceName="librefm"
          serviceDisplayName="Libre.FM"
          existingPermissions={permissions.librefm}
          externalUserId={loaderData.current_librefm_settings?.external_user_id}
          existingLatestListenedAt={
            loaderData.current_librefm_settings?.latest_listened_at
          }
        />

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">SoundCloud</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your SoundCloud account to play music on ListenBrainz.
            </p>
            <br />
            <div className="music-service-selection">
              <form>
                <ServicePermissionButton
                  service="soundcloud"
                  current={permissions.soundcloud}
                  value="listen"
                  title="Play music on ListenBrainz"
                  details="Connect to your SoundCloud account to play music using SoundCloud on ListenBrainz."
                  handlePermissionChange={handlePermissionChange}
                />
                <ServicePermissionButton
                  service="soundcloud"
                  current={permissions.soundcloud}
                  value="disable"
                  title="Disable"
                  details="You will not be able to listen to music on ListenBrainz using SoundCloud."
                  handlePermissionChange={handlePermissionChange}
                />
              </form>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Apple Music</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your Apple Music account to play music on ListenBrainz.
              <br />
              <small>
                Full length track playback requires a Apple Music subscription.
                <br />
                You will need to repeat the sign-in process every 6 months.
              </small>
            </p>
            <br />
            <div className="music-service-selection">
              <form>
                <ServicePermissionButton
                  service="appleMusic"
                  current={permissions.appleMusic}
                  value="listen"
                  title="Play music on ListenBrainz"
                  details="Play music using Apple Music on ListenBrainz."
                  handlePermissionChange={handleAppleMusicPermissionChange}
                />
                <ServicePermissionButton
                  service="appleMusic"
                  current={permissions.appleMusic}
                  value="disable"
                  title="Disable"
                  details="You won't be able to listen to music on ListenBrainz using Apple Music."
                  handlePermissionChange={handleAppleMusicPermissionChange}
                />
              </form>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Funkwhale</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your Funkwhale server to play music on ListenBrainz.
            </p>
            {permissions.funkwhale !== "listen" && (
              <div
                className="alert alert-warning alert-dismissible fade show"
                role="alert"
              >
                <strong>Important:</strong> You must be already logged into your
                Funkwhale server before connecting it to ListenBrainz.
                <button
                  type="button"
                  className="btn-close"
                  data-bs-dismiss="alert"
                  aria-label="Close"
                />
              </div>
            )}
            <form onSubmit={handleFunkwhaleConnect}>
              <div className="flex flex-wrap" style={{ gap: "1em" }}>
                <div>
                  <label className="form-label" htmlFor="funkwhaleHostUrl">
                    Your Funkwhale server URL:
                  </label>
                  <input
                    type="url"
                    className="form-control"
                    id="funkwhaleHostUrl"
                    name="funkwhaleHostUrl"
                    placeholder={
                      permissions.funkwhale === "listen"
                        ? funkwhaleAuth?.instance_url ||
                          "Connected Funkwhale server"
                        : "https://funkwhale.funkwhale.test/"
                    }
                    defaultValue={funkwhaleAuth?.instance_url || ""}
                    readOnly={permissions.funkwhale === "listen"}
                  />
                </div>
              </div>
              <br />
              <div className="music-service-selection">
                <button
                  type="submit"
                  className="music-service-option"
                  style={{ width: "100%" }}
                  disabled={permissions.funkwhale === "listen"}
                >
                  <input
                    readOnly
                    type="radio"
                    id="funkwhale_listen"
                    name="funkwhale"
                    value="listen"
                    checked={permissions.funkwhale === "listen"}
                  />
                  <label htmlFor="funkwhale_listen">
                    <div className="title">
                      {permissions.funkwhale === "listen"
                        ? "Connected to"
                        : "Connect to"}{" "}
                      Funkwhale
                    </div>
                    <div className="details">
                      Connect to your Funkwhale server to play music on
                      ListenBrainz.
                    </div>
                  </label>
                </button>
                <ServicePermissionButton
                  service="funkwhale"
                  current={permissions.funkwhale}
                  value="disable"
                  title="Disable"
                  details="You will not be able to listen to music on ListenBrainz using Funkwhale."
                  handlePermissionChange={handlePermissionChange}
                />
              </div>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Navidrome</h3>
          </div>
          <div className="card-body">
            <p>
              Connect to your Navidrome server to play music on ListenBrainz.
            </p>
            {permissions.navidrome !== "listen" && (
              <div
                className="alert alert-warning alert-dismissible fade show"
                role="alert"
              >
                <strong>Important:</strong> Make sure your Navidrome server is
                accessible and you have the correct credentials.
                <button
                  type="button"
                  className="btn-close"
                  data-bs-dismiss="alert"
                  aria-label="Close"
                />
              </div>
            )}
            <form id="navidrome-form" onSubmit={handleNavidromeConnect}>
              <div className="flex flex-wrap" style={{ gap: "1em" }}>
                <div>
                  <label className="form-label" htmlFor="navidromeHostUrl">
                    Your Navidrome server URL:
                  </label>
                  <input
                    type="url"
                    className="form-control"
                    id="navidromeHostUrl"
                    name="navidromeHostUrl"
                    placeholder={
                      permissions.navidrome === "listen"
                        ? navidromeAuth?.instance_url ||
                          "Connected Navidrome server"
                        : "https://navidrome.example.com/"
                    }
                    value={navidromeEditValues.hostUrl}
                    onChange={(e) =>
                      setNavidromeEditValues((prev) => ({
                        ...prev,
                        hostUrl: e.target.value,
                      }))
                    }
                    readOnly={
                      !navidromeIsEditing && permissions.navidrome === "listen"
                    }
                    required={
                      navidromeIsEditing || permissions.navidrome !== "listen"
                    }
                  />
                </div>
                <div>
                  <label className="form-label" htmlFor="navidromeUsername">
                    Username:
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="navidromeUsername"
                    name="navidromeUsername"
                    placeholder={
                      permissions.navidrome === "listen"
                        ? navidromeAuth?.username || "Connected user"
                        : "Navidrome username"
                    }
                    value={navidromeEditValues.username}
                    onChange={(e) =>
                      setNavidromeEditValues((prev) => ({
                        ...prev,
                        username: e.target.value,
                      }))
                    }
                    readOnly={
                      !navidromeIsEditing && permissions.navidrome === "listen"
                    }
                    required={
                      navidromeIsEditing || permissions.navidrome !== "listen"
                    }
                  />
                </div>
                {(navidromeIsEditing || permissions.navidrome !== "listen") && (
                  <div>
                    <label className="form-label" htmlFor="navidromePassword">
                      Password:
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      id="navidromePassword"
                      name="navidromePassword"
                      placeholder="Navidrome password"
                      required
                    />
                  </div>
                )}
                <div style={{ flex: 0, alignSelf: "end" }}>
                  <button
                    disabled={permissions.navidrome !== "listen"}
                    type="button"
                    className={`btn ${navidromeEditButtonClass}`}
                    onClick={handleNavidromeEditToggle}
                  >
                    {navidromeIsEditing ? "Save" : "Edit"}
                  </button>
                </div>
              </div>
              <br />
              <div className="music-service-selection">
                {permissions.navidrome !== "listen" && (
                  <button
                    type="submit"
                    className="music-service-option"
                    style={{ width: "100%" }}
                  >
                    <input
                      readOnly
                      type="radio"
                      id="navidrome_listen"
                      name="navidrome"
                      value="listen"
                      checked={false}
                    />
                    <label htmlFor="navidrome_listen">
                      <div className="title">Connect to Navidrome</div>
                      <div className="details">
                        Connect to your Navidrome server to play music on
                        ListenBrainz.
                      </div>
                    </label>
                  </button>
                )}
                {permissions.navidrome === "listen" && (
                  <div className="music-service-option connected">
                    <input
                      readOnly
                      type="radio"
                      id="navidrome_connected"
                      name="navidrome"
                      value="listen"
                      checked
                    />
                    <label htmlFor="navidrome_connected">
                      <div className="title">Connected to Navidrome</div>
                      <div className="details">
                        Your Navidrome server is connected and ready to play
                        music on ListenBrainz.
                      </div>
                    </label>
                  </div>
                )}
                <ServicePermissionButton
                  service="navidrome"
                  current={permissions.navidrome}
                  value="disable"
                  title="Disable"
                  details="You will not be able to listen to music on ListenBrainz using Navidrome."
                  handlePermissionChange={handlePermissionChange}
                />
              </div>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Youtube</h3>
          </div>
          <div className="card-body">
            <p>
              Playing music using YouTube on ListenBrainz does not require an
              account to be connected.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
