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
    relationships: { tracks: { data: Array<{ id: string; type: "tracks" }> } };
    type: "searchResults";
    id: string;
    attributes: {
      query: string;
      trackingId: string;
    };
  }>;
  included: Array<TidalTrack>;
};
