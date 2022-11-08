/** Main entities */
declare type MusicBrainzArtist = {
  area: string;
  begin_year: number;
  rels: { [key: string]: string };
  //   rels: Record<string, string>;
  type: string;
};

declare type MusicBrainzRecordingRel = {
  artist_mbid: string;
  artist_name: string;
  instrument?: string;
  type: string;
};

/** Tags / Genres / Moods */
declare type EntityTag = {
  count: number;
  genre_mbid?: string;
  tag: string;
};

declare type RecordingTag = EntityTag;

declare type ArtistTag = EntityTag & {
  artist_mbid: string;
};

declare type ReleaseGroupTag = EntityTag & {
  release_group_mbid: string;
};

declare type ListenMetadata = {
  artist?: {
    name?: string;
    artists?: Array<MusicBrainzArtist>;
  };
  recording?: {
    rels?: Array<MusicBrainzRecordingRel>;
    duration?: number;
  };
  release?: {
    caa_id: ?number;
    mbid?: string;
    year?: number;
    release_group_mbid?: string;
  };
  tag?: {
    artist?: Array<ArtistTag>;
    recording?: Array<RecordingTag>;
    release_group?: Array<ReleaseGroupTag>;
  };
};

declare type MetadataLookup = {
  metadata: ListenMetadata;
  artist_credit_name: string;
  artist_mbids: string[];
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};
