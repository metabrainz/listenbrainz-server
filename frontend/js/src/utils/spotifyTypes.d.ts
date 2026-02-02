declare type SpotifyUser = {
  access_token?: string;
  permission?: Array<SpotifyPermission>;
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
  loading: boolean;
  position: number;
  duration: number;
  track_window: {
    current_track: SpotifyTrack | null;
    previous_tracks: SpotifyTrack[];
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

declare type SoundCloudTrack = {
  id: number;
  permalink_url: string;
  artwork_url: string;
  title: string;
  uri: string;
  duration: number;
  user: {
    id: string;
    username: string;
  };
};
