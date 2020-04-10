/* eslint-disable no-undef */

// TODO: make this type specific
export type Listen = any;

export type ListenType = "single" | "playingNow" | "import";

// TODO: make this type specific
export type SubmitListensPayload = any;

export interface ImporterProps {
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

export interface ImporterState {
  show: boolean;
  canClose: boolean;
  lastfmUsername: string;
  msg: string;
}

export interface ModalProps {
  disable: boolean;
  children: React.ReactElement[];
  onClose(event: React.MouseEvent<HTMLButtonElement>): void;
}

export interface LastFmScrobblePage {
  recenttracks: {
    track: any
  }
}
