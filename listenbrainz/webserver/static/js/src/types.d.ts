/* eslint-disable camelcase */

declare module "react-responsive";
declare module "spotify-web-playback-sdk";
declare module "time-ago";
declare module "debounce-async";

declare module "react-bs-notifier";
declare type AlertType = "danger" | "warning" | "success";
declare type Alert = {
  id: number;
  type: AlertType;
  headline: string;
  message: string | JSX.Element;
  count?: number;
};

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

declare type BaseListenFormat = {
  listened_at: number;
  user_name?: string | null;
  track_metadata: {
    artist_name: string;
    release_name?: string | null;
    track_name: string;
    additional_info?: AdditionalInfo;
  };
};

declare type Listen = BaseListenFormat & {
  listened_at_iso?: string | null;
  playing_now?: boolean | null;
};

declare type Recommendation = BaseListenFormat;

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
  | "user-read-private"
  | "playlist-modify-public"
  | "playlist-modify-private";

declare type SpotifyImage = {
  height: number | null;
  url: string;
  width: number | null;
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

declare type SpotifyAPIError = {
  error: {
    status: number;
    message: string;
  };
};

declare type SpotifyPlaylistTrackObject = {
  added_at: string; // ISO 8601 datetime string	The date and time the track or episode was added.
  // Note: that some very old playlists may return null in this field.
  added_by: SpotifyUserObject; // The Spotify user who added the track or episode.
  // Note: that some very old playlists may return null in this field.
  is_local: boolean; //	Whether this track or episode is a local file or not.
  track: SpotifyTrack; //	Information about the track or episode.
};

declare type SpotifyUserObject = {
  display_name: string; //	The name displayed on the user’s profile. null if not available.
  external_urls: Array<{ [key: string]: string }>; // external URL object	Known public external URLs for this user.
  followers: { href: string | null; total: number }; // followers object	Information about the followers of this user.
  href: string; //	A link to the Web API endpoint for this user.
  id: string; //	The Spotify user ID for this user.
  images: SpotifyImage[]; // of image objects	The user’s profile image.
  type: string; //	The object type: “user”
  uri: string; // The Spotify URI for this user.
};

declare type SpotifyPlaylistObject = {
  collaborative: boolean; //	true if the owner allows other users to modify the playlist.
  description: string | null; // The playlist description. Only returned for modified, verified playlists, otherwise null.
  external_urls: Array<{ [key: string]: string }>; // external URL object Known external URLs for this playlist.
  followers: { href: string | null; total: number }; // followers object Information about the followers of the playlist.
  href: string; // A link to the Web API endpoint providing full details of the playlist.
  id: string; // The Spotify ID for the playlist.
  images: SpotifyImage[]; // array of image objects Images for the playlist. The array may be empty or contain up to three images. The images are returned by size in descending order. See Working with Playlists. Note: If returned, the source URL for the image ( url ) is temporary and will expire in less than a day.
  name: string; // The name of the playlist.
  owner: SpotifyUserObject; // public user object The user who owns the playlist
  public: boolean | null; // The playlist’s public/private status: true the playlist is public, false the playlist is private, null the playlist status is not relevant. For more about public/private status, see Working with Playlists.
  snapshot_id: string; // The version identifier for the current playlist. Can be supplied in other requests to target a specific playlist version: see Remove tracks from a playlist
  tracks: SpotifyPlaylistTrackObject[]; // array of playlist track objects inside a paging object Information about the tracks of the playlist.
  type: string; // The object type: “playlist”
  uri: string; // The Spotify URI for the playlist.
};

declare type SpotifyPagingObject<T> = {
  href: string; //	A link to the Web API endpoint returning the full result of the request.
  items: T[]; //	The requested data.
  limit: number; //	The maximum number of items in the response (as set in the query or by default).
  next: string; //	URL to the next page of items. ( null if none)
  offset: number; //	The offset of the items returned (as set in the query or by default).
  previous: string; //	URL to the previous page of items. ( null if none)
  total: number; //	The maximum number of
};

// the spotify-web-playback-sdk types are a bit messy
// Adding an any here for now.
// TODO: remove this any eventually
declare type SpotifyPlayerType = any | Spotify.SpotifyPlayer;

// Expect either a string or an Error or an html Response object
declare type BrainzPlayerError =
  | string
  | { message?: string; status?: number; statusText?: string };

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

declare type ListensListMode = "listens" | "recent";

declare type ListenFeedBack = 1 | 0 | -1;

declare type RecommendationFeedBack = "love" | "like" | "hate" | "dislike";

declare type FeedbackResponse = {
  recording_msid: string;
  score: ListenFeedBack;
  user_id: string;
};

declare type RecommendationFeedbackResponse = {
  recording_mbid: string;
  rating: RecommendationFeedBack;
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

declare type JSPFPlaylistExtension = {
  collaborators: string[];
  public: boolean;
  created_for?: string;
  copied_from?: string; // Full ListenBrainz playlist URI
  last_modified_at?: string; // ISO date string
};

declare type JSPFTrackExtension = {
  added_by: string;
  artist_identifier: string[]; // Full MusicBrainz artist URIs
  added_at: string; // ISO date string
  release_identifier?: string; // Full MusicBrainz release URI
};

declare type JSPFPlaylist = {
  title: string;
  creator: string;
  annotation?: string;
  info?: string;
  location?: string;
  identifier: string;
  image?: string;
  date: string; // ISO date string
  license?: string;
  attribution?: Array<{ location: string } | { identifier: string }>;
  link?: Array<{ [name: string]: string }>;
  meta?: Array<{ [name: string]: string }>;
  track: Array<JSPFTrack>;
  extension?: {
    [name: string]: any;
    "https://musicbrainz.org/doc/jspf#playlist"?: JSPFPlaylistExtension;
  };
};

declare type JSPFTrack = {
  id?: string; // React-sortable library expects an id attribute, this is not part of JSPF specification
  location?: string[];
  identifier: string;
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
  extension?: {
    [name: string]: any;
    "https://musicbrainz.org/doc/jspf#track"?: JSPFTrackExtension;
  };
};

declare type RecommendationFeedbackMap = {
  [recordingMbid: string]: RecommendationFeedBack | null;
};

/** For recommending a track from the front-end */
declare type UserTrackRecommendationMetadata = {
  artist_name: string;
  track_name: string;
  release_name?: string;
  recording_mbid?: string;
  recording_msid: string;
  artist_msid: string;
};

/** ***********************************
 ********  USER FEED TIMELINE  ********
 ************************************* */

type EventTypeT =
  | "recording_recommendation"
  | "listen"
  | "like"
  | "follow"
  | "stop_follow"
  | "block_follow"
  | "playlist_created";

type UserRelationshipEvent = {
  user_name_0: string;
  user_name_1: string;
  relationship_type: "follow";
  created: number;
};
type EventMetadata = Listen | JSPFPlaylist | UserRelationshipEvent;

type TimelineEvent = {
  event_type: EventTypeT;
  user_name: string;
  created: number;
  metadata: EventMetadata;
};
