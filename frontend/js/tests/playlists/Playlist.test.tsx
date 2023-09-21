import * as React from "react";
import { shallow, mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import AsyncSelect from "react-select/async";
import { act } from "react-dom/test-utils";
import PlaylistPage, {
  PlaylistPageProps,
  PlaylistPageState,
} from "../../src/playlists/Playlist";
import * as playlistPageProps from "../__mocks__/playlistPageProps.json";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import { MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION } from "../../src/playlists/utils";
import { waitForComponentToPaint } from "../test-utils";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

jest.mock("../../src/utils/SearchTrackOrMBID");

const { labsApiUrl, currentUser, playlist } = playlistPageProps;

const props = {
  labsApiUrl,
  playlist: playlist as JSPFObject,
};

const GlobalContextMock: GlobalAppContextT = {
  APIService: new APIService("foo"),
  youtubeAuth: {
    api_key: "fake-api-key",
  },
  spotifyAuth: {
    access_token: "heyo",
    permission: ["streaming"] as Array<SpotifyPermission>,
  },
  currentUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

describe("PlaylistPage", () => {
  it("renders correctly", () => {
    // Mock timeago (returns an elapsed time string) otherwise snapshot won't match
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = mount<PlaylistPage>(<PlaylistPage {...props} />, {
      wrappingComponent: GlobalAppContext.Provider,
      wrappingComponentProps: {
        value: GlobalContextMock,
      },
    });
    expect(wrapper.find("#playlist")).toHaveLength(1);
    const h1 = wrapper.find("h1");
    expect(h1).toHaveLength(1);
    expect(h1.getDOMNode()).toHaveTextContent("1980s flashback jams");
    expect(wrapper.getDOMNode()).toHaveTextContent(/Your lame 80s music/i);
  });

  it("hides exportPlaylistToSpotify button if playlist permissions are absent", () => {
    const wrapper = mount<PlaylistPage>(<PlaylistPage {...props} />, {
      wrappingComponent: GlobalAppContext.Provider,
      wrappingComponentProps: {
        value: GlobalContextMock,
      },
    });
    expect(wrapper.find("#exportPlaylistToSpotify")).toHaveLength(0);
  });

  it("shows exportPlaylistToSpotify button if playlist permissions are present", () => {
    const alternativeContextMock = {
      ...GlobalContextMock,
      spotifyAuth: {
        access_token: "heyo",
        refresh_token: "news",
        permission: [
          "playlist-modify-public",
          "playlist-modify-private",
          "streaming",
        ] as Array<SpotifyPermission>,
      },
    };
    const wrapper = mount<PlaylistPage>(<PlaylistPage {...props} />, {
      wrappingComponent: GlobalAppContext.Provider,
      wrappingComponentProps: {
        value: alternativeContextMock,
      },
    });
    expect(wrapper.find("#exportPlaylistToSpotify")).toHaveLength(1);
  });
});
