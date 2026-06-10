declare type TidalUser = {
  access_token?: string;
  client_id?: string;
};

declare type TidalTrack = {
  id: string;
  title: string;
  artist: { name: string };
  album: { title: string; cover?: string };
  duration: number;
};

declare type TidalSearchResult = {
  data: Array<{
    resource: TidalTrack;
  }>;
};
