import { createContext, createRef } from "react";
import APIService from "./APIService";
import RecordingFeedbackManager from "./RecordingFeedbackManager";

export type GlobalAppContextT = {
  APIService: APIService;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  soundcloudAuth?: SoundCloudUser;
  critiquebrainzAuth?: MetaBrainzProjectUser;
  musicbrainzAuth?: MetaBrainzProjectUser;
  userPreferences?: UserPreferences;
  musicbrainzGenres?: string[];
  recordingFeedbackManager: RecordingFeedbackManager;
};
const apiService = new APIService(`${window.location.origin}/1`);

const GlobalAppContext = createContext<GlobalAppContextT>({
  APIService: apiService,
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  soundcloudAuth: {},
  critiquebrainzAuth: {},
  musicbrainzAuth: {},
  userPreferences: {},
  musicbrainzGenres: [],
  recordingFeedbackManager: new RecordingFeedbackManager(apiService),
});

export default GlobalAppContext;
