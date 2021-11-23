import { createContext } from "react";
import APIService from "./APIService";

export type GlobalAppContextT = {
  APIService: APIService;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  critiquebrainzAuth?: CritiqueBrainzUser;
};

const GlobalAppContext = createContext<GlobalAppContextT>({
  APIService: new APIService(`${window.location.origin}/1`),
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {},
});

export default GlobalAppContext;
