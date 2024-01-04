import * as React from "react";

import { capitalize } from "lodash";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import ServicePermissionButton from "../components/ExternalServiceButton";

type MusicServicesLoaderData = {
  current_spotify_permissions: string;
  current_critiquebrainz_permissions: string;
  current_soundcloud_permissions: string;
};

export default function MusicServices() {
  const loaderData = useLoaderData() as MusicServicesLoaderData;

  const [permissions, setPermissions] = React.useState({
    spotify: loaderData.current_spotify_permissions,
    critiquebrainz: loaderData.current_critiquebrainz_permissions,
    soundcloud: loaderData.current_soundcloud_permissions,
  });

  const handlePermissionChange = async (
    serviceName: string,
    newValue: string
  ) => {
    try {
      const response = await fetch(
        `/profile/music-services/${serviceName}/disconnect/`,
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

  return (
    <div id="user-profile">
      <h2 className="page-title">Connect with third-party music services</h2>

      <div className="panel panel-default">
        <div className="panel-heading">
          <h3 className="panel-title">Spotify</h3>
        </div>
        <div className="panel-body">
          <p>
            Connect to your Spotify account to read your listening history, play
            music on ListenBrainz (requires Spotify Premium) or both. We
            encourage users to choose both options for the best experience, but
            you may also choose only one option. For music playing, make sure
            your browser allows autoplaying media on listenbrainz.org. If you
            have a Spotify account connected, you&apos;ll have much better
            results. Otherwise, we will search for a match on YouTube. If you
            ever face an issue, try disconnecting and reconnecting your Spotify
            account and make sure you select the permissions to &apos;record
            listens and play music&apos; or &apos;play music only&apos;.
          </p>
          <br />
          <div className="music-service-selection">
            <form onSubmit={(e) => e.preventDefault}>
              <ServicePermissionButton
                service="spotify"
                current={permissions.spotify}
                value="both"
                title="Activate both features (Recommended)"
                details="We will record your listening history permanently and make it available for others to view and explore. Discover and play songs directly on ListenBrainz, and import/export your playlist to and from Spotify."
                handlePermissionChange={handlePermissionChange}
              />
              <ServicePermissionButton
                service="spotify"
                current={permissions.spotify}
                value="listen"
                title="Play music on ListenBrainz"
                details="Discover and play songs directly on ListenBrainz, and import/export your playlist to and from Spotify. Note: Full length track playback requires Spotify Premium"
                handlePermissionChange={handlePermissionChange}
              />
              <ServicePermissionButton
                service="spotify"
                current={permissions.spotify}
                value="import"
                title="Record listening history"
                details="We will record your listening history permanently and make it available for others to view and explore."
                handlePermissionChange={handlePermissionChange}
              />
              <ServicePermissionButton
                service="spotify"
                current={permissions.spotify}
                value="disable"
                title="Disable"
                details="Spotify integration will be disabled. You won't be able to import your listens or listen to music on ListenBrainz using Spotify."
                handlePermissionChange={handlePermissionChange}
              />
            </form>
          </div>

          <h3>A note about permissions</h3>

          <p>
            In order to enable the feature to record your listens you will need
            to grant the permission to view your recent listens and your current
            listen.
          </p>

          <p>
            In order to play tracks on the ListenBrainz pages you will need to
            grant the permission to play streams from your account and create
            playlists. Oddly enough, Spotify also requires the permission to
            read your email address, your private information and your birthdate
            in order to play tracks. These permissions are required to determine
            if you are a premium user and can play full length tracks or will be
            limited to 30 second previews. However,{" "}
            <b>ListenBrainz will never read these pieces of data</b>. We
            promise! Please feel free to
            <a href="https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/spotify_updater/spotify_read_listens.py">
              inspect our source
            </a>{" "}
            code yourself!
          </p>

          <p>
            You can revoke these permissions whenever you want by unlinking your
            Spotify account.
          </p>
        </div>
      </div>

      <div className="panel panel-default">
        <div className="panel-heading">
          <h3 className="panel-title">CritiqueBrainz</h3>
        </div>
        <div className="panel-body">
          <p>
            Connect to your CritiqueBrainz account to publish reviews for your
            Listens directly from ListenBrainz. Your reviews will be
            independently visible on CritiqueBrainz and appear publicly on your
            CritiqueBrainz profile unless removed. To view or delete your
            reviews, visit your CritiqueBrainz profile.
          </p>
          <br />
          <div className="music-service-selection">
            <form>
              <ServicePermissionButton
                service="critiquebrainz"
                current={permissions.critiquebrainz}
                value="review"
                title="Publish reviews for your Listens"
                details="You will be able to publish mini-reviews for your Listens directly from ListenBrainz."
                handlePermissionChange={handlePermissionChange}
              />
              <ServicePermissionButton
                service="critiquebrainz"
                current={permissions.critiquebrainz}
                value="disable"
                title="Disable"
                details="You will not be able to publish mini-reviews for your Listens directly from ListenBrainz."
                handlePermissionChange={handlePermissionChange}
              />
            </form>
          </div>
        </div>
      </div>

      <div className="panel panel-default">
        <div className="panel-heading">
          <h3 className="panel-title">SoundCloud</h3>
        </div>
        <div className="panel-body">
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

      <div className="panel panel-default">
        <div className="panel-heading">
          <h3 className="panel-title">Youtube</h3>
        </div>
        <div className="panel-body">
          <p>
            ListenBrainz integrates with YouTube to let you play music tracks
            from ListenBrainz pages. You do not need to do anything to enable
            this. ListenBrainz will automatically search for tracks on YouTube
            and play one if it finds a match.
          </p>
        </div>
      </div>
    </div>
  );
}

export const MusicServicesLoader = async () => {
  const response = await fetch("/profile/music-services/details/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return { ...data };
};
