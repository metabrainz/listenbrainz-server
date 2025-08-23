declare type NavidromeUser = {
  md5_auth_token?: string; // MD5 hash token for authentication
  instance_url: string;
  salt?: string; // Random salt for authentication
  username: string;
  user_id: string;
};

declare type NavidromeTrack = {
  id: string;
  title: string;
  artist: string;
  album: string;
  albumId: string;
  duration: number;
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

declare type NavidromeAuthParams = {
  u: string; // username
  t: string; // token (MD5 hash)
  s: string; // salt
  v: string; // version
  c: string; // client
  f: string; // format
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
