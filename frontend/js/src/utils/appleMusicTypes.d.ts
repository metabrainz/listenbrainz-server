declare type AppleMusicUser = {
  developer_token?: string;
  music_user_token?: string;
};

declare type AppleMusicPlayerType = MusicKit.MusicKitInstance;

declare type AppleMusicPlaylistObject = {
  id: string; // The Apple Music ID for the playlist.
  type: string; // The object type: “playlist”
  href: string; // A link to the Web API endpoint providing full details of the playlist.
  attributes: AppleMusicPlaylistAtrributes;
  relationships?: AppleMusicPlaylistRelationships;
};

declare type AppleMusicPlaylistAtrributes = {
  lastModifiedDate: string;
  canEdit: boolean;
  name: string; // The name of the playlist.
  description: AppleMusicPlaylistDescriptionObject; // The playlist description. Only returned for modified, verified playlists, otherwise null.
  isPublic: boolean; //	true if the owner allows other users to modify the playlist.
  artwork?: AppleMusicPlaylistArtwork;
  hasCatalog: boolean;
  playParams?: AppleMusicPlaylistPlayParams;
};

declare type AppleMusicPlaylistPlayParams = {
  id: string;
  kind: string;
  isLibrary?: boolean;
};

declare type AppleMusicPlaylistDescriptionObject = {
  short: string | null;
  standard: string;
};

declare type AppleMusicRelationships = {
  tracks: AppleMusicPlaylistTrackObject[];
};

declare type AppleMusicPlaylistTrackObject = {
  href: string;
  next: string | null;
  data: AppleMusicTrack; //	Information about the track.
};

declare type AppleMusicTrack = {
  id: string;
  type: string;
  href: string;
  attributes: AppleMusicTrackAttributes;
};

declare type AppleMusicTrackAttributes = {
  albumName: string;
  artistName: string;
  artistUrl: string;
  artwork: AppleMusicTrackArtwork;
  attribution?: string;
  audioVariants?: Array<string>;
  composerName?: string;
  contentRating?: string;
  discNumber?: number;
  durationInMillis: number;
  editorialNotes?: AppleMusicTrackEditorialNotes;
  genreNames: Array<string>;
  hasLyrics: boolean;
  isAppleDigitalMaster: boolean;
  isrc?: string;
  name: string;
  playParams: AppleMusicTrackPlayParameters;
  previews?: Array<AppleMusicTrackPreview>;
  releaseDate: string;
  trackNumber: number;
  url: string;
  workName: string;
};

declare type AppleMusicTrackArtwork = {
  width: number;
  height: number;
  url: string;
};

declare type AppleMusicTrackPlayParameters = {
  id: string;
  kind: string;
};
