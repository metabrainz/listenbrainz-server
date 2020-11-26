/* eslint-disable camelcase */

declare module "react-responsive";
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
  score?: number;
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

// Expect either a string or an Error or an html Response object
declare type BrainzPlayerError =
  | string
  | { message?: string; status?: number; statusText?: string };

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
    range: UserStatsAPIRange;
    total_artist_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserReleasesResponse = {
  payload: {
    releases: Array<{
      artist_mbids?: Array<string>;
      artist_msid?: string;
      artist_name: string;
      release_mbid?: string;
      release_msid?: string;
      release_name: string;
      listen_count: number;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_release_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserRecordingsResponse = {
  payload: {
    recordings: Array<{
      artist_mbids?: Array<string>;
      artist_msid?: string;
      artist_name: string;
      release_mbid?: string;
      release_msid?: string;
      release_name?: string;
      track_name: string;
      recording_mbid?: string;
      recording_msid?: string;
      listen_count: number;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_recording_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserEntityResponse =
  | UserArtistsResponse
  | UserReleasesResponse
  | UserRecordingsResponse;

declare type UserStatsAPIRange = "all_time" | "year" | "month" | "week";

declare type UserEntityDatum = {
  id: string;
  entity: string;
  entityType: Entity;
  entityMBID?: string;
  artist?: string;
  artistMBID?: Array<string>;
  release?: string;
  releaseMBID?: string;
  idx: number;
  count: number;
};

declare type UserEntityData = Array<UserEntityDatum>;

declare type Entity = "artist" | "release" | "recording";

declare type UserListeningActivityResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    listening_activity: Array<{
      from_ts: number;
      to_ts: number;
      time_range: string;
      listen_count: number;
    }>;
  };
};

declare type UserListeningActivityDatum = {
  id: string;
  lastRangeCount?: number;
  thisRangeCount?: number;
  lastRangeTs?: number;
  thisRangeTs?: number;
};

declare type UserListeningActivityData = Array<UserListeningActivityDatum>;

declare type UserDailyActivityDatum = {
  day: string;
  [hour: number]: number;
};

declare type UserDailyActivityData = Array<UserDailyActivityDatum>;

declare type UserDailyActivityResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    daily_activity: {
      [day: string]: Array<{
        hour: number;
        listen_count: number;
      }>;
    };
  };
};

declare type UserArtistMapResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    artist_map: Array<{
      country: string;
      artist_count: number;
      listen_count: number;
    }>;
  };
};

declare type UserArtistMapDatum = {
  id: string;
  value: number;
};

declare type UserArtistMapData = Array<UserArtistMapDatum>;

declare type ListensListMode = "listens" | "follow" | "recent" | "cf_recs";

declare type ListenFeedBack = 1 | 0 | -1;

declare type FeedbackResponse = {
  recording_msid: string;
  score: ListenFeedBack;
  user_id: string;
};

declare type RecordingFeedbackMap = {
  [recordingMsid: string]: ListenFeedBack;
};

declare type ACRMSearchResult = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

// XSPF/JSPF format: https://www.xspf.org/jspf/
declare type JSPFObject = {
  playlist: JSPFPlaylist;
};
declare type JSPFPlaylist = {
  title: string;
  creator: string;
  annotation?: string;
  info?: string;
  location?: string;
  identifier: string;
  image?: string;
  date: string;
  license?: string;
  attribution?: Array<{ location: string } | { identifier: string }>;
  link?: Array<{ [name: string]: string }>;
  meta?: Array<{ [name: string]: string }>;
  track: Array<JSPFTrack>;
  extension?: { [name: string]: any };
};
declare type JSPFTrack = {
  location?: string[];
  identifier: string[];
  title: string;
  creator: string;
  annotation?: string;
  info?: string;
  image?: string;
  album?: string;
  trackNum?: number;
  duration?: number;
  link?: Array<{ [name: string]: string }>;
  meta?: Array<{ [name: string]: string }>;
  extension?: { [name: string]: any };
};
declare type ListenBrainzTrack = JSPFTrack & {
  id: string; // React-sortable library expects an id attribute
  added_at: string;
  added_by: string;
};

// LB stores more information about the playlist
// the doesn't fit in the JSPF format
declare type ListenBrainzPlaylist = JSPFPlaylist & {
  id: string; // Playlist MBID (without full URL)
  public: boolean;
  item_count: number; // or track_count ?
  last_modified: string; // ISO format?
  created_for?: string;
  copied_from?: string;
  collaborators?: string[];
};
