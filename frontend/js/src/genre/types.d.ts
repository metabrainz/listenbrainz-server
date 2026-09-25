export type TaggedEntity = {
  mbid: string;
  name: string;
  tag_count: number;
};

export type TaggedReleaseGroupEntity = TaggedEntity & {
  date?: string | null;
  type?: string | null;
  caa_id?: number | null;
  caa_release_mbid?: string | null;
  artist_credit_name?: string;
  artists?: Array<MBIDMappingArtist>;
  total_listen_count?: number | null;
  total_user_count?: number | null;
};

export type TaggedEntityGroup<T = TaggedEntity> = {
  count: number;
  entities: Array<T>;
};

export type TaggedRecordingEntity = import("../track/Track").Recording & {
  tag_count?: number;
  total_listen_count?: number;
  total_user_count?: number;
};

export type TaggedArtistEntity = TaggedEntity & {
  total_listen_count?: number | null;
  total_user_count?: number | null;
};

export type TaggedEntities = {
  artist: TaggedEntityGroup<TaggedArtistEntity>;
  release_group: TaggedEntityGroup<TaggedReleaseGroupEntity>;
  recording: TaggedEntityGroup<TaggedRecordingEntity>;
};

export type Genre = {
  name: string;
};

export type GenrePageProps = {
  genre: Genre;
  genre_mbid: string;
  entities: TaggedEntities;
  coverArt?: string;
};
