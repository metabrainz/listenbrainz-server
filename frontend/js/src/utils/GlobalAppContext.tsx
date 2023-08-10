import { createContext, createRef } from "react";
import APIService from "./APIService";

export type GlobalAppContextT = {
  APIService: APIService;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  critiquebrainzAuth?: MetaBrainzProjectUser;
  musicbrainzAuth?: MetaBrainzProjectUser;
  userPreferences?: UserPreferences;
  musicbrainzGenres?: string[];
};

const GlobalAppContext = createContext<GlobalAppContextT>({
  APIService: new APIService(`${window.location.origin}/1`),
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {},
  musicbrainzAuth: {},
  userPreferences: {},
  musicbrainzGenres: [],
});

export default GlobalAppContext;
