import { createContext } from "react";
import APIService from "./APIService";
import RecordingFeedbackManager from "./RecordingFeedbackManager";
import { FlairEnum, FlairName, Flair } from "./constants";

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
  flair?: Flair;
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
  flair: FlairEnum.None,
};

const GlobalAppContext = createContext<GlobalAppContextT>(defaultGlobalContext);

export default GlobalAppContext;
