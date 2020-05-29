/* eslint-disable camelcase */
declare module "spotify-web-playback-sdk";
declare module "react-bs-notifier";
declare module "time-ago";

// TODO: Remove "| null" when backend stops sending fields with null
interface AdditionalInfo {
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
  youtube_id?: string | null;
  origin_url?: string | null;
  tags?: Array<string> | null;
  track_mbid?: string | null;
  tracknumber?: number | null;
  work_mbids?: Array<string> | null;
}

declare type Listen = {
  listened_at: number;
  listened_at_iso?: string | null;
  playing_now?: boolean | null;
  user_name?: string | null;
  track_metadata: {
    artist_name: string;
    release_name?: string | null;
    track_name: string;
    additional_info?: AdditionalInfo;
  };
};

declare type ListenBrainzUser = {
  id?: number;
  name: string;
  auth_token?: string;
};

declare type ListenType = "single" | "playingNow" | "import";

declare type BrainzPlayDirection = "up" | "down" | "hidden";

declare type SubmitListensPayload = {
  listen_type: "single" | "playing_now" | "import";
  payload: Array<Listen>;
};

declare type SpotifyUser = {
  access_token?: string;
  permission?: SpotifyPermission;
};

declare type SpotifyPermission =
  | "user-read-currently-playing"
  | "user-read-recently-played"
  | "streaming"
  | "user-read-birthdate"
  | "user-read-email"
  | "user-read-private";

declare type SpotifyImage = {
  height: number;
  url: string;
};

declare type SpotifyArtist = {
  uri: string;
  name: string;
};

declare type SpotifyTrack = {
  album: {
    uri: string;
    name: string;
    images: Array<SpotifyImage>;
  };
  artists: Array<SpotifyArtist>;
  id: string | null;
  is_playable: boolean;
  media_type: "audio" | "video";
  name: string;
  type: "track" | "episode" | "ad";
  uri: string;
};

declare type SpotifyPlayerTrackWindow = {
  device_id: string;
};

declare type SpotifyPlayerSDKState = {
  paused: boolean;
  position: number;
  duration: number;
  track_window: {
    current_track: SpotifyTrack;
  };
};

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

declare type FollowUsersPlayingNow = {
  [user: string]: Listen;
};

declare type LastFmScrobblePage = {
  recenttracks: {
    track: any;
  };
};

declare type UserArtistsResponse = {
  payload: {
    artists: Array<{
      artist_mbids?: Array<string>;
      artist_msid?: string;
      artist_name: string;
      listen_count: number;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserArtistsAPIRange;
    total_artist_count: number;
    user_id: string;
  };
};

declare type UserArtistsAPIRange = "all_time" | "year" | "month" | "week";
