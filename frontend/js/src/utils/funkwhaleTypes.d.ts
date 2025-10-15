declare type FunkwhaleUser = {
  access_token?: string;
  refresh_token?: string;
  instance_url: string;
  user_id: string;
  username: string;
};

declare type FunkwhaleTrack = {
  id: number;
  title: string;
  // Funkwhale API versions use artist_credit
  artist_credit?: Array<{
    artist: {
      id: number;
      name: string;
      mbid?: string;
      fid?: string;
    };
    credit: string;
    joinphrase: string;
    index: number;
  }>;
  // Funkwhale API version 1 uses artist object
  artist?: {
    id: number;
    name: string;
    mbid?: string;
    fid?: string;
  };
  album?: {
    id: number;
    title: string;
    mbid?: string;
    cover?: {
      uuid?: string;
      size?: number;
      mimetype?: string;
      creation_date?: string;
      urls?: {
        source?: string | null;
        original?: string;
        small_square_crop?: string;
        medium_square_crop?: string;
        large_square_crop?: string;
      };
    };
  };
  listen_url: string;
  fid?: string;
  duration: number;
  position?: number;
  mbid?: string;
  is_playable?: boolean;
  creation_date: string;
  modification_date: string;
};

declare type FunkwhaleAlbum = {
  id: number;
  title: string;
  artist: {
    id: number;
    name: string;
    mbid?: string;
  };
  mbid?: string;
  cover?: {
    uuid?: string;
    size?: number;
    mimetype?: string;
    creation_date?: string;
    urls?: {
      source?: string | null;
      original?: string;
      small_square_crop?: string;
      medium_square_crop?: string;
      large_square_crop?: string;
    };
  };
  creation_date: string;
  modification_date: string;
  tracks_count: number;
};

declare type FunkwhaleArtist = {
  id: number;
  name: string;
  mbid?: string;
  creation_date: string;
  modification_date: string;
  albums_count: number;
  tracks_count: number;
};
