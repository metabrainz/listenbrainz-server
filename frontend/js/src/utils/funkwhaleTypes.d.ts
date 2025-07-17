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
  artist: {
    id: number;
    name: string;
    mbid?: string;
  };
  artist_credit?: Array<{
    artist: {
      id: number;
      name: string;
      mbid?: string;
    };
  }>;
  album?: {
    id: number;
    title: string;
    mbid?: string;
    cover?: {
      large?: string;
      medium?: string;
      small?: string;
    };
  };
  listen_url: string;
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
    large?: string;
    medium?: string;
    small?: string;
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
