export type TaggedEntity = {
  mbid: string;
  name: string;
  tag_count: number;
};

export type TaggedReleaseGroupEntity = TaggedEntity & {
  has_metadata: boolean;
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
  entities: Array<T>;
};

type Recording = import("../track/Track").Recording;

export type TaggedRecordingEntity = (
  | Recording
  | (Pick<Recording, "recording_mbid" | "recording_name"> & {
      artist_credit_name?: null;
    })
) & {
  tag_count?: number;
  total_listen_count?: number | null;
  total_user_count?: number | null;
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
