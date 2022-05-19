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
declare type GenericTag = {
  count: number;
  genre_mbid?: string;
  tag: string;
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
    recording?: Array<GenericTag>;
    release?: Array<GenericTag>;
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

declare type MBRelease = {
  "status-id": string;
  title: string;
  asin: string;
  packaging: string;
  barcode: string;
  "label-info"?: MBLabel[] | null;
  date: string;
  country: string;
  quality: string;
  "release-events"?: MBReleaseEvent[] | null;
  "release-group": MBReleaseGroup;
  "cover-art-archive": CoverArtArchive;
  status: string;
  disambiguation: string;
  "packaging-id": string;
  id: string;
  media?: MBMedia[] | null;
};
declare type MBReleaseEvent = {
  area: MBArea;
  date: string;
};
declare type MBArea = {
  disambiguation: string;
  "type-id"?: null;
  id: string;
  name: string;
  type?: null;
  "iso-3166-1-codes"?: string[] | null;
  "sort-name": string;
};
declare type MBReleaseGroup = {
  id: string;
  disambiguation: string;
  "first-release-date": string;
  "primary-type": string;
  "secondary-type-ids"?: string[] | null;
  "secondary-types"?: string[] | null;
  title: string;
  "primary-type-id": string;
};

declare type MBLabel = {
  "catalog-number": string;
  label: {
    "sort-name": string;
    "type-id": string | null; // UUID
    disambiguation: string;
    "label-code": string | null;
    name: string;
    type: string | null;
    id: string; // UUID
  };
};
declare type CoverArtArchive = {
  darkened: boolean;
  back: boolean;
  front: boolean;
  artwork: boolean;
  count: number;
};
declare type MBMedia = {
  format: string;
  "track-offset": number;
  tracks?: MBTrack[] | null;
  "track-count": number;
  position: number;
  title: string;
  "format-id": string;
};
declare type MBTrack = {
  recording: MBRecording;
  id: string;
  title: string;
  position: number;
  number: string;
  length: number;
};
declare type MBRecording = {
  id: string;
  "first-release-date": string;
  length: number;
  video: boolean;
  title: string;
  disambiguation: string;
};
