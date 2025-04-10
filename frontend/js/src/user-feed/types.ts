export type FeedFetchParams = { minTs?: number; maxTs?: number };

export enum FeedModes {
  Follows = "follows",
  Similar = "similar",
}

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  PERSONAL_RECORDING_RECOMMENDATION = "personal_recording_recommendation",
  RECORDING_PIN = "recording_pin",
  LIKE = "like",
  LISTEN = "listen",
  FOLLOW = "follow",
  STOP_FOLLOW = "stop_follow",
  BLOCK_FOLLOW = "block_follow",
  NOTIFICATION = "notification",
  REVIEW = "critiquebrainz_review",
  THANKS = "thanks",
}
