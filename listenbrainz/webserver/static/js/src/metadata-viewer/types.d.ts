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
declare type ArtistTag = {
  artist_mbid: string;
  count: number;
  genre_mbid?: string;
  tag: string;
};
declare type RecordingTag = {
  count: number;
  genre_mbid?: string;
  tag: string;
};

declare type ReleaseGroupTag = RecordingTag & {
  release_group_mbid: string;
};

declare type ListenMetadata = {
  artist?: Array<MusicBrainzArtist>;
  recording?: {
    rels?: Array<MusicBrainzRecordingRel>;
    duration?: number;
  };
  release?: {
    caa_id: ?number;
    mbid?: string;
    year?: number;
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
