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

declare type PlayingNowMetadata = {
  artist: Array<MusicBrainzArtist>;
  recording: {
    rels: Array<MusicBrainzRecordingRel>;
  };
  tag: {
    artist: Array<ArtistTag>;
    recording: Array<RecordingTag>;
  };
};
