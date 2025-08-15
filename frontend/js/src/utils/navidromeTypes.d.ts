declare type NavidromeUser = {
  encrypted_password?: string; // Encrypted password for authentication
  instance_url: string;
  username: string;
  user_id: string;
  salt?: string; // Fresh random salt generated for each request
};

declare type NavidromeTrack = {
  id: string;
  title: string;
  artist: string;
  album: string;
  duration: number;
  year?: number;
  genre?: string;
  trackNumber?: number;
  discNumber?: number;
  albumArtist?: string;
  path: string;
  suffix: string;
  contentType: string;
  isDir: boolean;
  isVideo: boolean;
  playCount: number;
  starred?: string;
  albumId: string;
  artistId: string;
  type: string;
  bookmarkPosition?: number;
  originalWidth?: number;
  originalHeight?: number;
  bitRate?: number;
  size: number;
  created: string;
  updated: string;
};

declare type NavidromeAlbum = {
  id: string;
  name: string;
  artist: string;
  artistId: string;
  coverArt?: string;
  songCount: number;
  duration: number;
  playCount: number;
  created: string;
  starred?: string;
  year?: number;
  genre?: string;
};

declare type NavidromeArtist = {
  id: string;
  name: string;
  coverArt?: string;
  albumCount: number;
  starred?: string;
};

declare type NavidromePlaylist = {
  id: string;
  name: string;
  comment?: string;
  owner: string;
  public: boolean;
  songCount: number;
  duration: number;
  created: string;
  changed: string;
  coverArt?: string;
  allowedUser?: string[];
  entry?: NavidromeTrack[];
};

declare type NavidromeSearchResult = {
  artist?: NavidromeArtist[];
  album?: NavidromeAlbum[];
  song?: NavidromeTrack[];
};

declare type NavidromeResponse<T> = {
  "subsonic-response": {
    status: "ok" | "failed";
    version: string;
    type: string;
    serverVersion: string;
    openSubsonic: boolean;
  } & T;
};
