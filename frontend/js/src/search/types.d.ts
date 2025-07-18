type PlaylistTypeSearchResult = {
  count: number;
  offset: number;
  playlist_count: number;
  playlists: {
    playlist: {
      annotation?: string;
      creator: string;
      date: string;
      identifier: string;
      title: string;
    };
  }[];
};

type TrackTypeSearchResult = {
  count: number;
  offset: number;
  recordings: {
    id: string;
    title: string;
    length: number;
    disambiguation: string;
    "artist-credit": {
      name: string;
      joinphrase?: string;
      artist: {
        id: string;
        name: string;
      };
    }[];
    releases: {
      id: string;
      title: string;
      "artist-credit": {
        name: string;
        joinphrase?: string;
      }[];
      "release-groups": {
        id: string;
        title: string;
      }[];
    }[];
  }[];
};

type Alias = {
  "sort-name": string;
  "type-id": string;
  name: string;
  locale: string | null;
  type: string;
  primary: boolean | null;
  "begin-date": number | null;
  "end-date": number | null;
};

type ArtistTypeSearchResult = {
  count: number;
  offset: number;
  artists: {
    name: string;
    id: string;
    type?: string;
    country?: string;
    gender?: string;
    "sort-name"?: string;
    disambiguation?: string;
    area?: {
      name: string;
    };
    aliases?: Alias[];
  }[];
};

type AlbumTypeSearchResult = {
  count: number;
  offset: number;
  "release-groups": {
    id: string;
    title: string;
    "primary-type"?: string;
    "first-release-date"?: string;
    "artist-credit": {
      name: string;
      joinphrase?: string;
      artist: {
        id: string;
        name: string;
      };
    }[];
    releases: {
      id: string;
      title: string;
    }[];
  }[];
};
