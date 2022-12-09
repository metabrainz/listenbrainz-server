import { createContext, createRef } from "react";
import APIService from "./APIService";
import SimpleModal from "./SimpleModal";

export type GlobalAppContextT = {
  APIService: APIService;
  currentUser: ListenBrainzUser;
  spotifyAuth?: SpotifyUser;
  youtubeAuth?: YoutubeUser;
  critiquebrainzAuth?: CritiqueBrainzUser;
  modal?: React.RefObject<SimpleModal> | null;
};

const GlobalAppContext = createContext<GlobalAppContextT>({
  APIService: new APIService(`${window.location.origin}/1`),
  currentUser: {} as ListenBrainzUser,
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {},
  modal: createRef<SimpleModal>(),
});

export default GlobalAppContext;
