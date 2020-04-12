declare module "spotify-web-playback-sdk";
declare module "react-bs-notifier";
declare module "time-ago";

// TODO: make this type specific
declare type Listen = any;
declare type ListenBrainzUser = any;

declare type ListenType = "single" | "playingNow" | "import";

declare type SpotifyPlayDirection = "up" | "down" | "hidden";
// TODO: make this type specific
declare type SubmitListensPayload = any;

declare type SpotifyUser = {
  access_token: string;
  permission: string;
};

declare type SpotifyPermission = any; // TODO
declare type SpotifyTrack = any; // TODO
declare type SpotifyArtist = any; // TODO
declare type SpotifyDeviceID = any; // TODO
declare interface SpotifyImage {
  height: number;
}
declare type SpotifyPlayerTrackWindow = any; // TODO
declare type SpotifyPlayerSDKState = any;

// the spotify-web-playback-sdk types are a bit messy
// Adding an any here for now.
// TODO: remove this any eventually
declare type SpotifyPlayerType = any | Spotify.SpotifyPlayer;

declare type AlertType = "danger" | "warning" | "success";
declare type Alert = {
  id: number;
  type: AlertType;
  title: string;
  message: string | JSX.Element;
};

declare type User = {
  id?: number;
  name: string;
  auth_token?: string;
};

declare type LastFmScrobblePage = {
declare type FollowUsersPlayingNow = any;

declare interface ImporterProps {
  user: {
    id?: string;
    name: string;
    auth_token: string;
  };
  profileUrl?: string;
  apiUrl?: string;
  lastfmApiUrl: string;
  lastfmApiKey: string;
}

declare interface ImporterState {
  show: boolean;
  canClose: boolean;
  lastfmUsername: string;
  msg: string;
}

declare interface ModalProps {
  disable: boolean;
  children: React.ReactElement[];
  onClose(event: React.MouseEvent<HTMLButtonElement>): void;
}

declare interface LastFmScrobblePage {
  recenttracks: {
    track: any;
  };
};
