import { createContext, createRef } from "react";
import APIService from "./APIService";

export type GlobalAppContextT = {
  APIService: APIService;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  critiquebrainzAuth?: CritiqueBrainzUser;
  userPreferences?: UserPreferences;
};

const GlobalAppContext = createContext<GlobalAppContextT>({
  APIService: new APIService(`${window.location.origin}/1`),
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {},
  userPreferences: {},
});

export default GlobalAppContext;
