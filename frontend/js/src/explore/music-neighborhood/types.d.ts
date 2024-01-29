type ArtistNodeInfo = {
  artist_mbid: string;
  name: string;
  comment?: string;
  type?: string;
  gender?: string;
  score?: number;
  reference_mbid?: string;
};

type NodeType = {
  id: string;
  artist_mbid: string;
  artist_name: string;
  size: number;
  color: string;
  score: number;
};

type LinkType = {
  source: string;
  target: string;
  distance: number;
};

type GraphDataType = {
  nodes: Array<NodeType>;
  links: Array<LinkType>;
};

type ArtistInfoType = {
  area: string;
  artist_mbid: string;
  born: string | number;
  gender?: string;
  link: string;
  name: string;
  topAlbum: ReleaseGroupType | null;
  topTracks: RecordingType[] | null;
  type: string;
  wiki: string;
};

type ReleaseColor = {
  blue: number;
  green: number;
  red: number;
};

type RecordingType = {
  artist_mbids: Array<string>;
  artist_name: string;
  artists: Array<MBIDMappingArtist>;
  caa_id: number;
  caa_release_mbid: string;
  length: number;
  recording_mbid: string;
  recording_name: string;
  release_color: ReleaseColor;
  release_mbid: string;
  release_name: string;
  total_listen_count: number;
  total_user_count: number;
};

type ReleaseGroupType = {
  artist: {
    artist_credit_id: number;
    name: string;
    artists: Array<MusicBrainzArtist>;
  };
  release: {
    caa_id: number;
    caa_release_mbid: string;
    date: string;
    name: string;
    type: string;
  };
  release_color: ReleaseColor;
  release_group: {
    caa_id: number;
    caa_release_mbid: string;
    date: string;
    name: string;
    type: string;
  };
  release_group_mbid: string;
  tag: {
    artist: Array<ArtistTag>;
    release_group: Array<ReleaseGroupTag>;
  };
  total_listen_count: number;
  total_user_count: number;
};
