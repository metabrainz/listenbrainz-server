/** Main entities */
declare type MusicBrainzArtist = {
  name: string;
  artist_mbid: string;
  join_phrase?: string;
  area: string;
  begin_year?: number;
  end_year?: number;
  rels: { [key: string]: string };
  //   rels: Record<string, string>;
  type: string;
  tag?: {
    artist: Array<ArtistTag>;
  };
  gender: string;
};

declare type MusicBrainzArtistCredit = {
  name: string;
  joinphrase: string;
  artist: {
    name: string;
    "sort-name": string;
    id: string;
    disambiguation: string;
    type: string | null;
    "type-id": string;
  };
};

declare type MusicBrainzReleaseGroup = {
  title: string;
  id: string;
  disambiguation: string;
  "first-release-date": string;
  "primary-type": string;
  "primary-type-id": string;
  "secondary-types": string[];
  "secondary-type-ids": string[];
};
declare type MusicBrainzLabel = {
  "catalog-number": string;
  label?:{id:string;name:string};
}

declare type MusicBrainzTrack = {
  number: string;
  length: number;
  position: number;
  title: string;
  id: string;
  recording: Omit<MusicBrainzRecording, "artist-credit">;
};
declare type MusicBrainzMedia = {
  title: string;
  position: number;
  tracks: Array<MusicBrainzTrack | (MusicBrainzTrack & WithArtistCredits)>;
  format: string;
  "format-id": string;
  "track-offset": number;
  "track-count": number;
};
declare type MusicBrainzRelease = {
  title: string;
  id: string;
  packaging: string;
  "packaging-id": string;
  date: string;
  status: string;
  barcode: string | number;
  "status-id": string;
  disambiguation: string;
  quality: string;
  country: string;
  "label-info"?: MusicBrainzLabel[];
};
// With ?inc=media
declare type WithMedia = {
  media: Array<MusicBrainzMedia>;
};
// With ?inc=artist-credits
declare type WithArtistCredits = {
  "artist-credit": Array<MusicBrainzArtistCredit>;
};
// With ?inc=release-groups
declare type WithReleaseGroup = {
  "release-group": MusicBrainzReleaseGroup;
};
// With ?inc=releases
declare type WithReleases = {
  releases: MusicBrainzRelease[];
};

declare type MusicBrainzRecording = {
  title: string;
  id: string;
  "first-release-date": string;
  length: number;
  video: boolean;
  disambiguation: string;
  "artist-credit": Array<MusicBrainzArtistCredit>;
};
// With ?inc=releases
declare type MusicBrainzRecordingWithReleases = MusicBrainzRecording & {
  releases: Array<MusicBrainzRelease>;
};
// With ?inc=releases+release-groups
declare type MusicBrainzRecordingWithReleasesAndRGs = MusicBrainzRecording & {
  releases: Array<MusicBrainzRelease & WithReleaseGroup>;
};

declare type MusicBrainzRecordingRel = {
  artist_mbid: string;
  artist_name: string;
  instrument?: string;
  type: string;
};

declare type WikipediaExtract = {
  url: string;
  content: string; // HTML string
  title: string;
  canonical: string;
  language: string;
};

/** Tags / Genres / Moods */
declare type EntityTag = {
  count: number;
  genre_mbid?: string;
  tag: string;
};

declare type RecordingTag = EntityTag;
declare type ReleaseGroupTag = EntityTag;

declare type ArtistTag = EntityTag & {
  artist_mbid: string;
};

declare type ListenMetadata = {
  artist?: {
    name?: string;
    artists?: Array<MusicBrainzArtist>;
  };
  recording?: {
    name?: string;
    rels?: Array<MusicBrainzRecordingRel>;
    length?: number;
  };
  release?: {
    name?: string;
    caa_id?: number;
    caa_release_mbid?: string;
    mbid?: string;
    year?: number;
    album_artist_name?: string;
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
declare type ReleaseGroupMetadataLookupResponse = {
  [string]: ReleaseGroupMetadataLookup;
};
declare type ReleaseGroupMetadataLookup = {
  artist: {
    artist_credit_id: number;
    artists: MusicBrainzArtist[];
    name: string;
  };
  release: {
    name: string;
    rels: { [key: string]: string };
  };
  release_group: {
    name: string;
    date: string;
    type: string;
    rels: { [key: string]: string };
  };
  tag?: {
    artist?: Array<ArtistTag>;
    release_group?: Array<ReleaseGroupTag>;
  };
};
