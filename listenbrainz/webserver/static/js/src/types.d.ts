declare interface ImporterProps {
  user: {
    id: string;
    name: string;
    auth_token: string;
  };
  profileUrl: string;
  apiUrl: string;
  lastfmApiUrl: string;
  lastfmApiKey: string;
}

declare interface ImporterState {
  show: boolean;
  canClose: boolean;
  lastfmUsername: string;
  msg: string;
}
