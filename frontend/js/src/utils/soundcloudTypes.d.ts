declare type SoundCloudUser = {
  access_token?: string;
};

declare type SoundCloudTrackObject = {
  id: string;
  permalink_url: string;
  artwork_url?: string;
  title: string;
  uri: string;
  duration: number;
  user: {
    id: string;
    username: string;
    avatar_url?: string;
  };
};

declare type SoundCloudPlaylistObject = {
  id: string;
  title: string;
  description?: string;
  tracks: SoundCloudTrackObject[];
  created_at: string;
  duration: number;
  artwork_url?: string;
  genre?: string;
  user: {
    id: number;
    username: string;
    avatar_url?: string;
  };
};

declare type SoundcloudAPIError = {
  code: integer;
  message: string;
  link: string;
};
