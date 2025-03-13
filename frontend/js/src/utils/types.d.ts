/* eslint-disable camelcase */

declare module "react-responsive";
declare module "spotify-web-playback-sdk";
declare module "musickit-typescript";

declare module "time-ago";
declare module "debounce-async";
// declaration typescript file doesn't exist for react-datetime-picker/dist/entry.nostyle.js so had to declare a dummy declaration.
declare module "react-datetime-picker/dist/entry.nostyle";

// TODO: Remove "| null" when backend stops sending fields with null
interface AdditionalInfo {
  artist_mbids?: Array<string> | null;
  discnumber?: number | null;
  duration_ms?: number | null;
  duration?: number | null;
  isrc?: string | null;
  listening_from?: string | null; // Deprecated
  music_service?: string | null;
  recording_mbid?: string | null;
  recording_msid?: string | null;
  release_artist_name?: string | null;
  release_artist_names?: Array<string> | null;
  release_group_mbid?: string | null;
  release_mbid?: string | null;
  spotify_album_artist_ids?: Array<string> | null;
  spotify_album_id?: string | null;
  spotify_artist_ids?: Array<string> | null;
  spotify_id?: string | null;
  submission_client?: string | null;
  youtube_id?: string | null;
  origin_url?: string | null;
  tags?: Array<string> | null;
  track_mbid?: string | null;
  tracknumber?: string | number | null;
  work_mbids?: Array<string> | null;
}

declare type MBIDMappingArtist = {
  artist_mbid: string;
  artist_credit_name: string;
  join_phrase: string;
};

declare type MBIDMapping = {
  recording_name?: string;
  recording_mbid: string;
  release_mbid: string;
  artist_mbids: Array<string>;
  artists?: Array<MBIDMappingArtist>;
  caa_id?: number;
  caa_release_mbid?: string;
  release_group_mbid?: string;
  release_group_name?: string;
};

declare type BaseListenFormat = {
  listened_at: number;
  user_name?: string | null;
  track_metadata: TrackMetadata;
};

declare type Listen = BaseListenFormat & {
  listened_at_iso?: string | null;
  playing_now?: boolean | null;
  inserted_at?: number;
};

declare type Recommendation = Listen & {
  latest_listened_at?: string;
};

declare type ListenBrainzUser = {
  id?: number;
  name: string;
  auth_token?: string;
};

declare type ImportService = "lastfm" | "librefm";

declare type ListenType = "single" | "playing_now" | "import";

declare type SubmitListensPayload = {
  listen_type: "single" | "playing_now" | "import";
  payload: Array<Listen>;
};

declare type YoutubeUser = {
  api_key?: string;
};

declare type SoundCloudUser = {
  access_token?: string;
};

declare type MetaBrainzProjectUser = {
  access_token?: string;
};

// Expect either a string or an Error or an html Response object
declare type BrainzPlayerError =
  | string
  | { message?: string; status?: number; statusText?: string };

declare type LastFmScrobblePage = {
  recenttracks: {
    track: any;
  };
};

declare type UserArtistsResponse = {
  payload: {
    artists: Array<{
      artist_mbid: string | null;
      artist_name: string;
      listen_count: number;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_artist_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserReleasesResponse = {
  payload: {
    releases: Array<{
      artist_mbids?: Array<string>;
      artist_name: string;
      release_mbid?: string;
      release_name: string;
      listen_count: number;
      caa_id?: number;
      caa_release_mbid?: string;
      artists?: Array<MBIDMappingArtist>;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_release_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserRecordingsResponse = {
  payload: {
    recordings: Array<{
      artist_mbids?: Array<string>;
      artist_name: string;
      release_mbid?: string;
      release_name?: string;
      track_name: string;
      recording_mbid?: string;
      recording_msid?: string;
      caa_id?: number;
      caa_release_mbid?: string;
      artists?: Array<MBIDMappingArtist>;
      listen_count: number;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_recording_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserReleaseGroupsResponse = {
  payload: {
    release_groups: Array<{
      artist_mbids?: Array<string>;
      artist_name: string;
      release_group_mbid?: string;
      release_group_name: string;
      listen_count: number;
      caa_id?: number;
      caa_release_mbid?: string;
      artists?: Array<MBIDMappingArtist>;
    }>;
    count: number;
    last_updated: number;
    offset: number;
    range: UserStatsAPIRange;
    total_release_group_count: number;
    user_id: string;
    from_ts: number;
    to_ts: number;
  };
};

declare type UserEntityResponse =
  | UserArtistsResponse
  | UserReleasesResponse
  | UserRecordingsResponse
  | UserReleaseGroupsResponse;

declare type UserStatsAPIRange =
  | "all_time"
  | "year"
  | "month"
  | "week"
  | "this_year"
  | "this_month"
  | "this_week";

declare type UserEntityDatum = {
  id: string;
  entity: string;
  entityType: Entity;
  entityMBID?: string;
  artist?: string;
  artistMBID?: Array<string>;
  release?: string;
  releaseMBID?: string;
  releaseGroup?: string;
  releaseGroupMBID?: string;
  idx: number;
  count: number;
  caaID?: number;
  caaReleaseMBID?: string;
  artists?: Array<MBIDMappingArtist>;
};

declare type UserEntityData = Array<UserEntityDatum>;

declare type Entity = "artist" | "release" | "recording" | "release-group";

declare type UserListeningActivityResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    listening_activity: Array<{
      from_ts: number;
      to_ts: number;
      time_range: string;
      listen_count: number;
    }>;
  };
};

declare type UserListeningActivityDatum = {
  id: string;
  lastRangeCount?: number;
  thisRangeCount?: number;
  lastRangeTs?: number;
  thisRangeTs?: number;
};

declare type UserListeningActivityData = Array<UserListeningActivityDatum>;

declare type UserDailyActivityDatum = {
  id: string;
  data: Array<{
    x: string | number;
    y: number;
  }>;
};

declare type UserDailyActivityData = Array<UserDailyActivityDatum>;

declare type UserDailyActivityResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    daily_activity: {
      [day: string]: Array<{
        hour: number;
        listen_count: number;
      }>;
    };
  };
};

declare type UserArtistActivityResponse = {
  result: Array<{
    name: string;
    listen_count: number;
    albums: Array<{
      name: string;
      listen_count: number;
      release_group_mbid: string;
    }>;
  }>;
};

declare type UserArtistMapArtist = {
  artist_name: string;
  artist_mbid: string;
  listen_count: number;
};

declare type UserArtistMapResponse = {
  payload: {
    from_ts: number;
    to_ts: number;
    last_updated: number;
    user_id: string;
    range: UserStatsAPIRange;
    artist_map: Array<{
      country: string;
      artist_count: number;
      listen_count: number;
      artists: Array<UserArtistMapArtist>;
    }>;
  };
};

declare type UserArtistMapDatum = {
  id: string;
  value: number;
  artists?: Array<UserArtistMapArtist>;
};

declare type UserArtistMapData = Array<UserArtistMapDatum>;

declare type ListenFeedBack = 1 | 0 | -1;

declare type RecommendationFeedBack = "love" | "like" | "hate" | "dislike";

declare type FeedbackResponse = {
  created: number;
  recording_msid: string;
  recording_mbid?: string | null;
  score: ListenFeedBack;
  user_id: string;
};
declare type TrackMetadata = {
  artist_name: string;
  track_name: string;
  release_name?: string;
  recording_mbid?: string;
  recording_msid?: string;
  release_mbid?: string;
  additional_info?: AdditionalInfo;
  mbid_mapping?: MBIDMapping;
};

declare type FeedbackResponseWithTrackMetadata = FeedbackResponse & {
  track_metadata: TrackMetadata;
};

declare type RecommendationFeedbackResponse = {
  recording_mbid: string;
  rating: RecommendationFeedBack;
};

declare type RecordingFeedbackMap = {
  [recording_id: string]: ListenFeedBack;
};

declare type ACRMSearchResult = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

type CoverArtGridOptions = {
  dimension: number;
  layout: number;
};

// XSPF/JSPF format: https://www.xspf.org/jspf/
declare type JSPFObject = {
  playlist: JSPFPlaylist;
};

declare type JSPFPlaylistMetadata = {
  external_urls?: { [key: string]: any };
  algorithm_metadata?: {
    source_patch: string;
  };
  expires_at?: string; // ISO date string
  cover_art?: CoverArtGridOptions;
};

declare type JSPFPlaylistExtension = {
  collaborators?: string[];
  public: boolean;
  created_for?: string;
  copied_from?: string; // Full ListenBrainz playlist URI
  last_modified_at?: string; // ISO date string
  additional_metadata?: JSPFPlaylistMetadata;
};

declare type JSPFTrackExtension = {
  added_by: string;
  added_at: string; // ISO date string
  artist_identifiers?: string[]; // Full MusicBrainz artist URIs
  release_identifier?: string; // Full MusicBrainz release URI
  additional_metadata?: { [key: string]: any };
};

declare type JSPFPlaylist = {
  title: string;
  creator: string;
  annotation?: string;
  info?: string;
  location?: string;
  identifier: string;
  image?: string;
  date: string; // ISO date string
  license?: string;
  attribution?: Array<{ location: string } | { identifier: string }>;
  link?: Array<{ [name: string]: string }>;
  meta?: Array<{ [name: string]: string }>;
  track: Array<JSPFTrack>;
  extension?: {
    [name: string]: any;
    "https://musicbrainz.org/doc/jspf#playlist"?: JSPFPlaylistExtension;
  };
};

declare type JSPFTrack = {
  id?: string; // React-sortable library expects an id attribute, this is not part of JSPF specification
  location?: string[];
  identifier: string | string[];
  title: string;
  creator: string;
  annotation?: string;
  info?: string;
  image?: string;
  album?: string;
  trackNum?: number;
  duration?: number;
  link?: Array<{ [name: string]: string }>;
  meta?: Array<{ [name: string]: string }>;
  extension?: {
    [name: string]: any;
    "https://musicbrainz.org/doc/jspf#track"?: JSPFTrackExtension;
  };
};

declare type RecommendationFeedbackMap = {
  [recordingMbid: string]: RecommendationFeedBack | null;
};

declare type PinnedRecording = {
  blurb_content?: string | null;
  created: number;
  pinned_until: number;
  row_id: number;
  recording_mbid: string | null;
  recording_msid?: string;
  track_metadata: TrackMetadata;
};

/** For recommending a track from the front-end */
declare type UserTrackRecommendationMetadata = {
  recording_mbid?: string;
  recording_msid?: string;
};

/** For recommending a track personally from the front-end */
declare type UserTrackPersonalRecommendationMetadata = UserTrackRecommendationMetadata & {
  blurb_content: string;
  users: Array<string>;
  track_metadata?: TrackMetadata;
};

declare type PinEventMetadata = Listen & {
  blurb_content?: string;
};

/** ***********************************
 ********  USER FEED TIMELINE  ********
 ************************************* */

type EventTypeT =
  | "recording_recommendation"
  | "recording_pin"
  | "listen"
  | "like"
  | "follow"
  | "stop_follow"
  | "block_follow"
  | "notification"
  | "personal_recording_recommendation"
  | "critiquebrainz_review"
  | "thanks";

type UserRelationshipEventMetadata = {
  user_name_0: string;
  user_name_1: string;
  relationship_type: "follow";
  created: number;
};

type ThanksMetadata = {
  original_event_id: number;
  original_event_type: EventTypeT;
  blurb_content: string;
  thanker_id: number;
  thanker_username: string;
  thankee_id: number;
  thankee_username: string;
};

type NotificationEventMetadata = {
  message: string;
};

type EventMetadata =
  | Listen
  | UserRelationshipEventMetadata
  | PinEventMetadata
  | NotificationEventMetadata
  | UserTrackPersonalRecommendationMetadata
  | CritiqueBrainzReview
  | ThanksMetadata;

type TimelineEvent<T extends EventMetadata> = {
  event_type: EventTypeT;
  id?: number;
  user_name: string;
  created: number;
  metadata: T;
  hidden: boolean;
};

type SimilarUser = {
  name: string;
  similarityScore: number;
};

type ReviewableEntityType = "recording" | "artist" | "release_group";

type ReviewableEntity = {
  type: ReviewableEntityType;
  name?: string | null;
  mbid: string;
};

type CritiqueBrainzUser = {
  created: string;
  display_name: string;
  id: string;
  karma: number;
  musicbrainz_username: string;
  user_ref: string;
  user_type: string;
};

type CritiqueBrainzReview = {
  entity_id: string;
  entity_name: string;
  entity_type: ReviewableEntityType;
  review_mbid?: string;
  text: string;
  languageCode?: string;
  rating?: number;
  user_name?: string;
  published_on?: string;
};

type CritiqueBrainzReviewAPI = {
  created: string;
  edits: number;
  entity_id: string;
  entity_type: ReviewableEntityType;
  id: string; // id of the review
  full_name: string; // license
  info_url: string; // license
  is_draft: boolean;
  is_hidden: boolean;
  language: string;
  last_revision: {
    id: number;
    rating: number;
    review_id: string;
    text: string;
    timestamp: string;
  };
  last_updated: string;
  license_id: string;
  popularity: number;
  published_on: string;
  source: string | null;
  source_url: string | null;
  text: string | null;
  rating: number;
  user: CritiqueBrainzUser;
  votes_negative_count: number;
  votes_positive_count: number;
};

type CoverArtArchiveEntry = {
  types: string[]; // Array of types i.e ["Front", "Back"]
  front: boolean;
  back: boolean;
  edit: number;
  image: string; // "http://coverartarchive.org/release/76df3287-6cda-33eb-8e9a-044b5e15ffdd/829521842.jpg",
  comment: "";
  approved: true;
  id: string;
  thumbnails: {
    250: string; // Full URL to 250px version "http://coverartarchive.org/release/76df3287-6cda-33eb-8e9a-044b5e15ffdd/829521842-250.jpg",
    500: string;
    1200: string;
    small: string;
    large: string;
  };
};

type CoverArtArchiveResponse = {
  images: CoverArtArchiveEntry[];
  release: string; // Full MB URL i.e "http://musicbrainz.org/release/76df3287-6cda-33eb-8e9a-044b5e15ffdd"
};

type ColorReleaseItem = {
  artist_name: string;
  color: number[];
  dist: number;
  caa_id: number;
  release_name: string;
  release_mbid: string;
  recordings?: BaseListenFormat[];
};

type ColorReleasesResponse = {
  payload: {
    releases: Array<ColorReleaseItem>;
  };
};

type UnlinkedListens = {
  artist_name: string;
  listened_at: string;
  recording_name: string;
  release_name?: string | null;
  recording_msid: string;
};

type FreshReleaseItem = {
  artist_credit_name: string;
  artist_mbids: Array<string>;
  caa_id: number | null;
  caa_release_mbid: string | null;
  confidence?: number;
  release_date: string;
  release_group_mbid: string;
  release_group_primary_type?: string;
  release_group_secondary_type?: string;
  release_mbid: string;
  release_name: string;
  release_tags: Array<string>;
  listen_count: number;
};

type UserFreshReleasesResponse = {
  payload: {
    releases: Array<FreshReleaseItem>;
    user_id: string;
  };
};

declare type SearchUser = {
  user_name: string;
};

declare type BrainzPlayerSettings = {
  youtubeEnabled?: boolean;
  spotifyEnabled?: boolean;
  soundcloudEnabled?: boolean;
  appleMusicEnabled?: boolean;
  brainzplayerEnabled?: boolean;
  dataSourcesPriority?: Array<
    "spotify" | "youtube" | "soundcloud" | "appleMusic"
  >;
};


declare type UserPreferences = {
  saveData?: boolean;
  brainzplayer?: BrainzPlayerSettings;
};

declare type FeedbackForUserForRecordingsRequestBody = {
  recording_mbids: string[];
  recording_msids?: string[];
};

declare type BrainzPlayerQueueItem = Listen & {
  id: string;
};

declare type BrainzPlayerQueue = BrainzPlayerQueueItem[];
