import * as React from "react";
import { mount, shallow } from "enzyme";

import { act } from "react-dom/test-utils";
import { Link } from "react-router-dom";
import SpotifyPlayer from "../../../src/common/brainzplayer/SpotifyPlayer";
import APIService from "../../../src/utils/APIService";
import { DataSourceTypes } from "../../../src/common/brainzplayer/BrainzPlayer";
import GlobalAppContext from "../../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";

// Create a new instance of GlobalAppContext
const defaultContext = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {
    access_token: "heyo",
    permission: ["user-read-currently-playing"] as SpotifyPermission[],
  },
  currentUser: {} as ListenBrainzUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

const props = {
  refreshSpotifyToken: new APIService("base-uri").refreshSpotifyToken,
  show: true,
  playerPaused: false,
  onPlayerPausedChange: (paused: boolean) => {},
  onProgressChange: (progressMs: number) => {},
  onDurationChange: (durationMs: number) => {},
  onTrackInfoChange: (
    title: string,
    trackId: string,
    artist?: string,
    album?: string,
    artwork?: ReadonlyArray<MediaImage>
  ) => {},
  onTrackEnd: () => {},
  onTrackNotFound: () => {},
  handleError: (error: BrainzPlayerError, title?: string) => {},
  handleWarning: (message: string | JSX.Element, title?: string) => {},
  handleSuccess: (message: string | JSX.Element, title?: string) => {},
  onInvalidateDataSource: (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ) => {},
};

describe("SpotifyPlayer", () => {
  const permissionsErrorMessage = (
    <p>
      In order to play music with Spotify, you will need a Spotify Premium
      account linked to your ListenBrainz account.
      <br />
      Please try to{" "}
      <Link to="/settings/music-services/details/">
        link for &quot;playing music&quot; feature
      </Link>{" "}
      and refresh this page
    </p>
  );
  it("renders", () => {
    window.fetch = jest.fn();
    const wrapper = mount(<SpotifyPlayer {...props} />);
    expect(wrapper.getDOMNode()).toContainHTML(
      '<div data-testid="spotify-player" />'
    );
  });

  it("should play from spotify_id if it exists on the listen", async () => {
    const spotifyListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          spotify_id: "https://open.spotify.com/track/surprise!",
        },
      },
    };
    const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...props} />);
    const instance = wrapper.instance();

    instance.playSpotifyURI = jest.fn();
    instance.searchAndPlayTrack = jest.fn();
    // play listen should extract the spotify track ID
    await act(() => {
      instance.playListen(spotifyListen);
    });
    expect(instance.playSpotifyURI).toHaveBeenCalledTimes(1);
    expect(instance.playSpotifyURI).toHaveBeenCalledWith(
      "spotify:track:surprise!"
    );
    expect(instance.searchAndPlayTrack).not.toHaveBeenCalled();
  });

  describe("hasPermissions", () => {
    it("calls onInvalidateDataSource (via handleAccountError) if no access token or no permission", () => {
      const onInvalidateDataSource = jest.fn();
      const mockProps = {
        ...props,
        onInvalidateDataSource,
        spotifyUser: {},
      };
      expect(SpotifyPlayer.hasPermissions(mockProps.spotifyUser)).toEqual(
        false
      );
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        instance,
        permissionsErrorMessage
      );
    });

    it("calls onInvalidateDataSource if permissions insufficient", () => {
      const onInvalidateDataSource = jest.fn();
      const mockProps = {
        ...props,
        onInvalidateDataSource,
      };
      expect(SpotifyPlayer.hasPermissions(defaultContext.spotifyAuth)).toEqual(
        false
      );
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledTimes(1);
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        instance,
        permissionsErrorMessage
      );
    });
    it("should not call onInvalidateDataSource if permissions are accurate", async () => {
      const onInvalidateDataSource = jest.fn();
      const spotifyUser = {
        access_token: "FNORD",
        permission: [
          "streaming",
          "user-read-email",
          "user-read-private",
        ] as SpotifyPermission[],
      };
      expect(SpotifyPlayer.hasPermissions(spotifyUser)).toEqual(true);
      const mockProps = {
        ...props,
        onInvalidateDataSource,
      };
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...defaultContext,
            spotifyAuth: spotifyUser,
          }}
        >
          <SpotifyPlayer {...mockProps} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.find(SpotifyPlayer).instance() as SpotifyPlayer;

      expect.assertions(2);
      expect(instance.props.onInvalidateDataSource).not.toHaveBeenCalled();
    });
  });

  describe("handleAccountError", () => {
    it("calls onInvalidateDataSource", () => {
      const onInvalidateDataSource = jest.fn();
      const checkSpotifyToken = jest.fn();
      const spotifyUser = {
        access_token: "FNORD",
        permission: [
          "streaming",
          "user-read-email",
          "user-read-private",
        ] as SpotifyPermission[],
      };
      const mockProps = {
        ...props,
        onInvalidateDataSource,
        checkSpotifyToken,
      };
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...defaultContext,
            spotifyAuth: spotifyUser,
          }}
        >
          <SpotifyPlayer {...mockProps} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.find(SpotifyPlayer).instance() as SpotifyPlayer;

      instance.handleAccountError();
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledTimes(1);
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        instance,
        permissionsErrorMessage
      );
    });
  });

  describe("handleTokenError", () => {
    it("calls connectSpotifyPlayer", async () => {
      const handleError = jest.fn();
      const onTrackNotFound = jest.fn();
      const mockProps = {
        ...props,
        handleError,
        onTrackNotFound,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      instance.handleAccountError = jest.fn();
      instance.connectSpotifyPlayer = jest.fn();

      await instance.handleTokenError(new Error("Test"), () => {});
      expect(instance.handleAccountError).not.toHaveBeenCalled();
      // we recreate the spotify player and refresh the token all in one go
      expect(instance.connectSpotifyPlayer).toHaveBeenCalledTimes(1);
      expect(instance.props.handleError).not.toHaveBeenCalled();
      expect(instance.props.onTrackNotFound).not.toHaveBeenCalled();
    });

    it("calls handleAccountError if wrong tokens error thrown", async () => {
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...props} />);
      const instance = wrapper.instance();
      instance.handleAccountError = jest.fn();

      await instance.handleTokenError(
        new Error("Invalid token scopes."),
        () => {}
      );
      expect(instance.handleAccountError).toHaveBeenCalledTimes(1);
    });
  });
  describe("handlePlayerStateChanged", () => {
    const spotifyPlayerState: SpotifyPlayerSDKState = {
      paused: true,
      loading: false,
      position: 10,
      duration: 1000,
      track_window: {
        current_track: {
          album: {
            uri: "",
            name: "Album name",
            images: [{ url: "url/to/album-art.jpg", width: 200, height: 100 }],
          },
          artists: [
            { uri: "", name: "Track artist 1" },
            { uri: "", name: "Track artist 2" },
          ],
          id: "spotifyVideoId",
          is_playable: true,
          media_type: "audio",
          name: "Track name",
          type: "track",
          uri: "my-spotify-uri",
        },
        previous_tracks: [],
      },
    };
    it("calls onPlayerPausedChange if player paused state changes", async () => {
      const onPlayerPausedChange = jest.fn();
      const mockProps = { ...props, onPlayerPausedChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      await act(() => {
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
      onPlayerPausedChange.mockClear();

      await act(() => {
        // Emulate the prop change that the call to onPlayerPausedChange would have done
        wrapper.setProps({ playerPaused: true });
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });

      expect(instance.props.onPlayerPausedChange).not.toHaveBeenCalled();
      onPlayerPausedChange.mockClear();
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          paused: false,
        });
      });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("detects the end of a track", async () => {
      const onTrackEnd = jest.fn();
      const mockProps = { ...props, onTrackEnd };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      await act(() => {
        instance.handlePlayerStateChanged(spotifyPlayerState);
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });
      expect(instance.props.onTrackEnd).not.toHaveBeenCalled();

      const endOfTrackPlayerState = {
        ...spotifyPlayerState,
        // This is how we detect the end of a track
        // See https://github.com/spotify/web-playback-sdk/issues/35#issuecomment-509159445
        paused: true,
        position: 0,
        track_window: {
          ...spotifyPlayerState.track_window,
          previous_tracks: [
            {
              id: spotifyPlayerState.track_window.current_track?.id,
            } as SpotifyTrack,
          ],
        },
      };
      // Spotify has a tendency to send multiple messages in a short burst,
      // and we debounce calls to onTrackEnd
      instance.handlePlayerStateChanged(endOfTrackPlayerState);
      instance.handlePlayerStateChanged(endOfTrackPlayerState);
      instance.handlePlayerStateChanged(endOfTrackPlayerState);
      expect(onTrackEnd).toHaveBeenCalledTimes(1);
    });

    it("detects a new track and sends information up", async () => {
      const onTrackInfoChange = jest.fn();
      const mockProps = { ...props, onTrackInfoChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect(wrapper.state("durationMs")).toEqual(0);
      expect(wrapper.state("currentSpotifyTrack")).toBeUndefined();
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
        });
      });

      expect(instance.props.onTrackInfoChange).toHaveBeenCalledTimes(1);
      expect(
        instance.props.onTrackInfoChange
      ).toHaveBeenCalledWith(
        "Track name",
        "https://open.spotify.com/track/spotifyVideoId",
        "Track artist 1, Track artist 2",
        "Album name",
        [{ src: "url/to/album-art.jpg", sizes: "200x100" }]
      );
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(wrapper.state("currentSpotifyTrack")).toEqual(
        spotifyPlayerState.track_window.current_track
      );
    });

    it("updates track duration and progress", async () => {
      const onProgressChange = jest.fn();
      const onDurationChange = jest.fn();
      const mockProps = { ...props, onProgressChange, onDurationChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect(wrapper.state("durationMs")).toEqual(0);
      await act(() => {
        // First let it detect a track change
        instance.handlePlayerStateChanged({ ...spotifyPlayerState });
      });
      await act(() => {
        // Then change duration and position
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
          position: 123,
        });
      });

      expect(instance.props.onDurationChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onDurationChange).toHaveBeenCalledWith(1234);
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(123);
      onDurationChange.mockClear();
      onProgressChange.mockClear();

      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
          position: 125,
        });
      });
      expect(instance.props.onDurationChange).not.toHaveBeenCalled();
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(125);
    });
  });
});
