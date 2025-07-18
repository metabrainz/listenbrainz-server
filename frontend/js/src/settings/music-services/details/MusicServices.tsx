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
  current_librefm_permissions: string;
  current_lastfm_settings?: {
    external_user_id?: string;
    latest_listened_at?: string;
  };
  current_librefm_settings?: {
    external_user_id?: string;
    latest_listened_at?: string;
  };
};

export default function MusicServices() {
  const { spotifyAuth, soundcloudAuth, critiquebrainzAuth } = React.useContext(
    GlobalAppContext
  );

  const loaderData = useLoaderData() as MusicServicesLoaderData;

  const { appleAuth } = React.useContext(GlobalAppContext);

  const [permissions, setPermissions] = React.useState({
    spotify: loaderData.current_spotify_permissions,
    critiquebrainz: loaderData.current_critiquebrainz_permissions,
    soundcloud: loaderData.current_soundcloud_permissions,
    appleMusic: loaderData.current_apple_permissions,
    lastfm: loaderData.current_lastfm_permissions,
    librefm: loaderData.current_librefm_permissions,
  });

  const handlePermissionChange = async (
    serviceName: string,
    newValue: string
  ) => {
    try {
      const response = await fetch(
        `/settings/music-services/${serviceName}/disconnect/`,
        {
          method: "POST",
          body: JSON.stringify({ action: newValue }),
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

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
