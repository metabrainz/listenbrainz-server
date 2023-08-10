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
    expect(wrapper.html()).toMatchSnapshot();
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

  it("filters out playlist owner from collaborators", async () => {
    const wrapper = mount<PlaylistPage>(<PlaylistPage {...props} />, {
      wrappingComponent: GlobalAppContext.Provider,
      wrappingComponentProps: {
        value: GlobalContextMock,
      },
    });
    const instance = wrapper.instance();
    expect(
      instance.state.playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]
        ?.collaborators
    ).toEqual([]);

    const APISpy = jest
      .spyOn(instance.context.APIService, "editPlaylist")
      .mockResolvedValue(200);
    await act(async () => {
      await instance.editPlaylist(
        "FNORD",
        "I have seen the FNORDS, have you?",
        true,
        // Calling editPlaylist with playlist owner name, should be filtered out
        ["iliekcomputers", "mr_monkey"],
        "https://listenbrainz.org/playlist/4245ccd3-4f0d-4276-95d6-2e09d87b5546"
      );
    });

    expect(APISpy).toHaveBeenCalledWith(
      "merde-a-celui-qui-lit",
      "https://listenbrainz.org/playlist/4245ccd3-4f0d-4276-95d6-2e09d87b5546",
      {
        playlist: expect.objectContaining({
          extension: {
            "https://musicbrainz.org/doc/jspf#playlist": expect.objectContaining(
              {
                collaborators: ["mr_monkey"],
              }
            ),
          },
        }),
      }
    );
    expect(
      instance.state.playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]
        ?.collaborators
    ).toEqual(["mr_monkey"]);
    await waitForComponentToPaint(wrapper);
    expect(wrapper.find("[href='/user/mr_monkey']")).toHaveLength(1);
  });
});
