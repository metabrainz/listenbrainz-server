declare module "spotify-web-playback-sdk";
declare module "react-bs-notifier";
declare module "time-ago";

// TODO: Remove "| null" when backend stops sending fields with null
declare type Listen = {
  listened_at: number;
  listened_at_iso?: string | null;
  playing_now?: boolean | null;
  user_name?: string | null;
  track_metadata: {
    artist_name: string;
    release_name?: string | null;
    track_name: string;
    additional_info?: {
      artist_mbids?: Array<string> | null;
      artist_msid?: string | null;
      discnumber?: number | null;
      duration_ms?: number | null;
      isrc?: string | null;
      listening_from?: string | null;
      recording_mbid?: string | null;
      recording_msid?: string | null;
      release_artist_name?: string | null;
      release_artist_names?: Array<string> | null;
      release_group_mbid?: string | null;
      release_mbid?: string | null;
      release_msid?: string | null;
      spotify_album_artist_ids?: Array<string> | null;
      spotify_album_id?: string | null;
      spotify_artist_ids?: Array<string> | null;
      spotify_id?: string | null;
      tags?: Array<string> | null;
      track_mbid?: string | null;
      tracknumber?: number | null;
      work_mbids?: Array<string> | null;
      [key: string]: any;
    };
  };
};

declare type ListenBrainzUser = {
  id?: number;
  name: string;
  auth_token?: string;
};

declare type ListenType = "single" | "playingNow" | "import";

declare type SpotifyPlayDirection = "up" | "down" | "hidden";

declare type SubmitListensPayload = {
  listen_type: "single" | "playing_now" | "import";
  payload: Array<Listen>;
};

declare type SpotifyUser = {
  access_token: string;
  permission: string;
};

declare type SpotifyPermission = any; // TODO
declare type SpotifyTrack = any; // TODO
declare type SpotifyArtist = any; // TODO
declare type SpotifyDeviceID = any; // TODO
declare interface SpotifyImage {
  height: number;
}
declare type SpotifyPlayerTrackWindow = any; // TODO
declare type SpotifyPlayerSDKState = any;

// the spotify-web-playback-sdk types are a bit messy
// Adding an any here for now.
// TODO: remove this any eventually
declare type SpotifyPlayerType = any | Spotify.SpotifyPlayer;

declare type AlertType = "danger" | "warning" | "success";
declare type Alert = {
  id: number;
  type: AlertType;
  title: string;
  message: string | JSX.Element;
};

declare type FollowUsersPlayingNow = any;
declare type LastFmScrobblePage = {
  recenttracks: {
    track: any;
  };
};
