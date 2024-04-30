import { createContext } from "react";
import APIService from "./APIService";
import RecordingFeedbackManager from "./RecordingFeedbackManager";

export type GlobalAppContextT = {
  APIService: APIService;
  websocketsUrl: string;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  soundcloudAuth?: SoundCloudUser;
  critiquebrainzAuth?: MetaBrainzProjectUser;
  appleAuth?: AppleMusicUser;
  musicbrainzAuth?: MetaBrainzProjectUser & {
    refreshMBToken: () => Promise<string | undefined>;
  };
  userPreferences?: UserPreferences;
  musicbrainzGenres?: string[];
  recordingFeedbackManager: RecordingFeedbackManager;
};
const apiService = new APIService(`${window.location.origin}/1`);

export const defaultGlobalContext: GlobalAppContextT = {
  APIService: apiService,
  websocketsUrl: "",
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  soundcloudAuth: {},
  appleAuth: {},
  critiquebrainzAuth: {},
  musicbrainzAuth: {
    refreshMBToken: async () => {
      return undefined;
    },
  },
  userPreferences: {},
  musicbrainzGenres: [],
  recordingFeedbackManager: new RecordingFeedbackManager(apiService),
};

const GlobalAppContext = createContext<GlobalAppContextT>(defaultGlobalContext);

export default GlobalAppContext;
