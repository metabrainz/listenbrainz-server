import * as React from "react";
import { mount, shallow } from "enzyme";

import SpotifyPlayer from "./SpotifyPlayer";
import APIService from "./APIService";

const props = {
  spotifyUser: {
    access_token: "heyo",
    permission: "read" as SpotifyPermission,
  },
  refreshSpotifyToken: new APIService("base-uri").refreshSpotifyToken,
  show: true,
  playerPaused: false,
  onPlayerPausedChange: (paused: boolean) => {},
  onProgressChange: (progressMs: number) => {},
  onDurationChange: (durationMs: number) => {},
  onTrackInfoChange: (title: string, artist?: string) => {},
  onTrackEnd: () => {},
  onTrackNotFound: () => {},
  handleError: (error: string | Error, title?: string) => {},
  handleWarning: (message: string | JSX.Element, title?: string) => {},
  handleSuccess: (message: string | JSX.Element, title?: string) => {},
  onInvalidateDataSource: (message?: string | JSX.Element) => {},
};

describe("SpotifyPlayer", () => {
  it("renders", () => {
    window.fetch = jest.fn();
    const wrapper = mount(<SpotifyPlayer {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  describe("checkSpotifyToken", () => {
    it("calls onInvalidateDataSource (via handleAccountError) if no access token or no permission", () => {
      const onInvalidateDataSource = jest.fn();
      const mockProps = {
        ...props,
        onInvalidateDataSource,
        // Cheating a little bit on the type here, shhhh!
        spotifyUser: {} as SpotifyUser,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      const errorMsg = (
        <p>
          In order to play music, it is required that you link your Spotify
          Premium account.
          <br />
          Please try to{" "}
          <a href="/profile/connect-spotify" target="_blank">
            link for &quot;playing music&quot; feature
          </a>{" "}
          and refresh this page
        </p>
      );
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        errorMsg
      );
    });

    it("calls onInvalidateDataSource if permissions insufficient", () => {
      const onInvalidateDataSource = jest.fn();
      const mockProps = {
        ...props,
        onInvalidateDataSource,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledTimes(1);
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        "Permission to play songs not granted"
      );
    });
    it("should not call onInvalidateDataSource if permissions are accurate", async () => {
      const onInvalidateDataSource = jest.fn();
      const spotifyUser = {
        access_token: "FNORD",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      };
      const mockProps = {
        ...props,
        onInvalidateDataSource,
        spotifyUser,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect.assertions(2);
      expect(instance.props.onInvalidateDataSource).not.toHaveBeenCalled();
      await expect(
        instance.checkSpotifyToken(
          spotifyUser.access_token,
          spotifyUser.permission
        )
      ).resolves.toEqual(true);
    });
  });

  describe("handleAccountError", () => {
    it("calls onInvalidateDataSource", () => {
      const onInvalidateDataSource = jest.fn();
      const checkSpotifyToken = jest.fn();
      const spotifyUser = {
        access_token: "FNORD",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      };
      const mockProps = {
        ...props,
        onInvalidateDataSource,
        spotifyUser,
        checkSpotifyToken,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handleAccountError();
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledTimes(1);
      const errorMsg = (
        <p>
          In order to play music, it is required that you link your Spotify
          Premium account.
          <br />
          Please try to{" "}
          <a href="/profile/connect-spotify" target="_blank">
            link for &quot;playing music&quot; feature
          </a>{" "}
          and refresh this page
        </p>
      );
      expect(instance.props.onInvalidateDataSource).toHaveBeenCalledWith(
        errorMsg
      );
    });
  });

  describe("handleTokenError", () => {
    it("calls handleError and onTrackNotFound if refreshSpotifyToken throws", async () => {
      const handleError = jest.fn();
      const onTrackNotFound = jest.fn();
      const refreshSpotifyToken = jest
        .fn()
        .mockRejectedValue(
          new Error(
            "'To err is human,' but a human error is nothing to what a computer can do if it tries."
          )
        );
      const mockProps = {
        ...props,
        handleError,
        onTrackNotFound,
        refreshSpotifyToken,
      };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();
      instance.handleAccountError = jest.fn();
      instance.connectSpotifyPlayer = jest.fn();

      await instance.handleTokenError(new Error("Test"), () => {});
      expect(instance.handleAccountError).not.toHaveBeenCalled();
      expect(instance.connectSpotifyPlayer).not.toHaveBeenCalled();
      expect(instance.props.refreshSpotifyToken).toHaveBeenCalledTimes(1);
      expect(instance.props.handleError).toHaveBeenCalledTimes(1);
      expect(instance.props.handleError).toHaveBeenCalledWith(
        "'To err is human,' but a human error is nothing to what a computer can do if it tries.",
        "Spotify error"
      );
      expect(instance.props.onTrackNotFound).toHaveBeenCalledTimes(1);
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
      position: 10,
      duration: 1000,
      track_window: {
        current_track: {
          album: {
            uri: "",
            name: "Album name",
            images: [],
          },
          artists: [
            { uri: "", name: "Track artist 1" },
            { uri: "", name: "Track artist 2" },
          ],
          id: "1",
          is_playable: true,
          media_type: "audio",
          name: "Track name",
          type: "track",
          uri: "",
        },
      },
    };
    it("calls onPlayerPausedChange if player paused state changes", () => {
      const onPlayerPausedChange = jest.fn();
      const mockProps = { ...props, onPlayerPausedChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handlePlayerStateChanged(spotifyPlayerState);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
      onPlayerPausedChange.mockClear();

      // Emulate the prop change that the call to onPlayerPausedChange would have done
      wrapper.setProps({ playerPaused: true });

      instance.handlePlayerStateChanged(spotifyPlayerState);
      expect(instance.props.onPlayerPausedChange).not.toHaveBeenCalled();
      onPlayerPausedChange.mockClear();

      instance.handlePlayerStateChanged({
        ...spotifyPlayerState,
        paused: false,
      });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("detects the end of a track", () => {
      const onTrackEnd = jest.fn();
      const mockProps = { ...props, onTrackEnd };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      // Spotify has a tendency to send multiple messages in a short burst,
      // and we debounce calls to onTrackEnd
      instance.handlePlayerStateChanged({ ...spotifyPlayerState, position: 0 });
      instance.handlePlayerStateChanged({ ...spotifyPlayerState, position: 0 });
      instance.handlePlayerStateChanged({ ...spotifyPlayerState, position: 0 });
      expect(instance.props.onTrackEnd).toHaveBeenCalledTimes(1);
    });

    it("detects a new track and sends information up", () => {
      const onTrackInfoChange = jest.fn();
      const mockProps = { ...props, onTrackInfoChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect(wrapper.state("durationMs")).toEqual(0);
      expect(wrapper.state("currentSpotifyTrack")).toBeUndefined();
      instance.handlePlayerStateChanged({
        ...spotifyPlayerState,
        duration: 1234,
      });

      expect(instance.props.onTrackInfoChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onTrackInfoChange).toHaveBeenCalledWith(
        "Track name",
        "Track artist 1, Track artist 2"
      );
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(wrapper.state("currentSpotifyTrack")).toEqual(
        spotifyPlayerState.track_window.current_track
      );
    });

    it("updates track duration and progress", () => {
      const onProgressChange = jest.fn();
      const onDurationChange = jest.fn();
      const mockProps = { ...props, onProgressChange, onDurationChange };
      const wrapper = shallow<SpotifyPlayer>(<SpotifyPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect(wrapper.state("durationMs")).toEqual(0);
      // First let it detect a track change
      instance.handlePlayerStateChanged({ ...spotifyPlayerState });
      // Then change duration and position
      instance.handlePlayerStateChanged({
        ...spotifyPlayerState,
        duration: 1234,
        position: 123,
      });

      expect(instance.props.onDurationChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onDurationChange).toHaveBeenCalledWith(1234);
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(123);
      onDurationChange.mockClear();
      onProgressChange.mockClear();

      instance.handlePlayerStateChanged({
        ...spotifyPlayerState,
        duration: 1234,
        position: 125,
      });
      expect(instance.props.onDurationChange).not.toHaveBeenCalled();
      expect(wrapper.state("durationMs")).toEqual(1234);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(125);
    });
  });
});
