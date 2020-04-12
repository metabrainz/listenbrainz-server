declare module "spotify-web-playback-sdk";
// TODO: make this type specific
declare type Listen = any;

declare type ListenType = "single" | "playingNow" | "import";

declare type SpotifyPlayDirection = "up" | "down" | "hidden";
// TODO: make this type specific
declare type SubmitListensPayload = any;

declare interface SpotifyUser {
  access_token: string;
  permission: string;
}
declare type SpotifyPermission = any; // TODO
declare type SpotifyTrack = any; // TODO
declare type SpotifyArtist = any; // TODO
declare type SpotifyDeviceID = any; // TODO
declare interface SpotifyImage {
  height: number;
}
declare type SpotifyPlayerTrackWindow = any; // TODO
declare type AlertType = any; // TODO
declare type SpotifyPlayerSDKState = any;

// the spotify-web-playback-sdk types are a bit messy
// Adding an any here for now.
// TODO: remove this any eventually
declare type SpotifyPlayerType = any | Spotify.SpotifyPlayer;

declare type LastFmScrobblePage = {
  recenttracks: {
    track: any;
  };
};
