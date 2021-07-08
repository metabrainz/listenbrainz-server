import * as React from "react";
import { mount } from "enzyme";
import BrainzPlayer, { DataSourceType } from "./BrainzPlayer";
import SoundcloudPlayer from "./SoundcloudPlayer";
import YoutubePlayer from "./YoutubePlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import APIService from "./APIService";
import GlobalAppContext from "./GlobalAppContext";

const props = {
  direction: "up" as BrainzPlayDirection,
  onCurrentListenChange: (listen: Listen | JSPFTrack) => {},
  listens: [],
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => {},
};
const spotifyAccountWithPermissions = {
  access_token: "haveyouseenthefnords",
  permission: ["streaming", "user-read-email", "user-read-private"] as Array<
    SpotifyPermission
  >,
};

const GlobalContextMock = {
  context: {
    APIService: new APIService("base-uri"),
    spotifyAuth: {
      access_token: "heyo",
      permission: ["user-read-currently-playing"] as Array<SpotifyPermission>,
    },
    youtubeAuth: {
      api_key: "fake-api-key",
    },
    currentUser: { name: "" },
  },
};

// Give yourself a two minute break and go listen to this gem
// https://musicbrainz.org/recording/7fcaf5b3-e682-4ce6-be61-d3bce775a43f
const listen: Listen = {
  listened_at: 0,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
  },
};

describe("BrainzPlayer", () => {
  it("renders correctly", () => {
    const wrapper = mount<BrainzPlayer>(
      <BrainzPlayer {...props} />,
      GlobalContextMock
    );
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("creates Youtube and SoundCloud datasources by default", () => {
    const mockProps = {
      ...props,
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />, {
      context: { ...GlobalContextMock.context, spotifyUser: {} },
    });
    const instance = wrapper.instance();
    expect(instance.dataSources).toHaveLength(2);
    expect(instance.dataSources[0].current).toBeInstanceOf(YoutubePlayer);
    expect(instance.dataSources[1].current).toBeInstanceOf(SoundcloudPlayer);
  });

  it("creates a Spotify datasource when passed a spotify user with right permissions", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider
        value={{
          ...GlobalContextMock.context,
          spotifyAuth: spotifyAccountWithPermissions,
        }}
      >
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    expect(instance.dataSources[0].current).toBeInstanceOf(SpotifyPlayer);
  });

  it("removes a datasource when calling invalidateDataSource", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    instance.handleWarning = jest.fn();

    const datasourcesBefore = instance.dataSources.length;
    instance.invalidateDataSource(
      instance.dataSources[0].current as SpotifyPlayer,
      "Test message"
    );
    expect(instance.handleWarning).toHaveBeenCalledWith(
      "Test message",
      "Cannot play from this source"
    );
    expect(instance.dataSources).toHaveLength(datasourcesBefore - 1);
    instance.dataSources.forEach((dataSource) => {
      expect(dataSource.current).not.toBeInstanceOf(SpotifyPlayer);
    });
  });

  it("selects Youtube as source when listen has a youtube URL", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider
        value={{
          ...GlobalContextMock.context,
          spotifyAuth: spotifyAccountWithPermissions,
        }}
      >
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    expect(instance.dataSources[1].current).toBeInstanceOf(YoutubePlayer);
    const youtubeListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          origin_url: "https://www.youtube.com/watch?v=RW8SBwGNcF8",
        },
      },
    };
    // if origin_url is a youtube link, it should play it with YoutubePlayer instead of Spotify
    instance.playListen(youtubeListen);
    expect(instance.state.currentDataSourceIndex).toEqual(1);
  });

  it("selects Spotify as source when listen has listening_from = spotify", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider
        value={{
          ...GlobalContextMock.context,
          spotifyAuth: spotifyAccountWithPermissions,
        }}
      >
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    const spotifyListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          listening_from: "spotify",
        },
      },
    };
    // Try to play on youtube directly (index 1), should use spotify instead (index 0)
    instance.playListen(spotifyListen, 1);
    expect(instance.state.currentDataSourceIndex).toEqual(0);
  });

  it("selects Spotify as source when listen has a spotify_id", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider
        value={{
          ...GlobalContextMock.context,
          spotifyAuth: spotifyAccountWithPermissions,
        }}
      >
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    const spotifyListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          spotify_id: "doesn't matter in this test as long as it's here",
        },
      },
    };
    // Try to play on youtube directly (index 1), should use spotify instead (index 0)
    instance.playListen(spotifyListen, 1);
    expect(instance.state.currentDataSourceIndex).toEqual(0);
  });

  it("selects Soundcloud as source when listen has a soundcloud URL", () => {
    const wrapper = mount<BrainzPlayer>(
      <GlobalAppContext.Provider
        value={{
          ...GlobalContextMock.context,
          spotifyAuth: spotifyAccountWithPermissions,
        }}
      >
        <BrainzPlayer {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper.instance();
    expect(instance.dataSources[2].current).toBeInstanceOf(SoundcloudPlayer);
    const soundcloudListen: Listen = {
      listened_at: 42,
      track_metadata: {
        additional_info: {
          origin_url: "https://soundcloud.com/wankelmut/wankelmut-here-to-stay",
        },
        artist_name: "Wankelmut",
        release_name: "",
        track_name: "Rock'n'Roll Is Here To Stay",
      },
    };
    // if origin_url is a soundcloud link, it should play it with SoundcloudPlayer instead of Spotify
    instance.playListen(soundcloudListen);
    expect(instance.state.currentDataSourceIndex).toEqual(2);
  });

  describe("stopOtherBrainzPlayers", () => {
    it("gets called when playing a track or unpausing", async () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      // Hello! If you are reading these tests, please take a small break
      // and go listen to this beautiful short song below:
      const youtubeListen: Listen = {
        listened_at: 0,
        track_metadata: {
          artist_name: "Moondog",
          track_name: "Bird's Lament",
          additional_info: {
            origin_url: "https://www.youtube.com/watch?v=RW8SBwGNcF8",
          },
        },
      };

      const spy = jest.spyOn(instance, "stopOtherBrainzPlayers");

      // Initial play
      instance.playListen(youtubeListen);
      expect(spy).toHaveBeenCalled();

      // Emulate the player playing
      await instance.setState({ playerPaused: false });

      spy.mockReset();

      // Pause
      await instance.togglePlay();
      expect(spy).not.toHaveBeenCalled();

      // Emulate the player paused
      await instance.setState({ playerPaused: true });

      // Play again
      await instance.togglePlay();
      expect(spy).toHaveBeenCalled();
    });

    it("calls LocalStorage.setItem to fire event", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      const localStorageSpy = jest.spyOn(Storage.prototype, "setItem");
      const dateNowMock = jest.fn().mockReturnValue(1234567);
      Date.now = dateNowMock;

      instance.stopOtherBrainzPlayers();

      expect(localStorageSpy).toHaveBeenCalledWith(
        "BrainzPlayer_stop",
        "1234567"
      );
    });

    it("reacts to a LocalStorage event and pauses the player if currently playing", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener");
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.setState({ playerPaused: false });

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "storage",
        instance.onLocalStorageEvent
      );

      const togglePlaySpy = jest.fn();
      instance.dataSources[0].current!.togglePlay = togglePlaySpy;

      // Emulate "storage" event firing
      const event = new StorageEvent("storage", {
        key: "BrainzPlayer_stop",
        newValue: "1234567",
        storageArea: window.localStorage,
      });
      window.dispatchEvent(event);

      expect(togglePlaySpy).toHaveBeenCalled();
    });
    it("reacts to a LocalStorage event and does nothing if currently paused", () => {
      const addEventListenerSpy = jest.spyOn(window, "addEventListener");
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.setState({ playerPaused: false });

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "storage",
        instance.onLocalStorageEvent
      );

      const togglePlaySpy = jest.fn();
      instance.dataSources[0].current!.togglePlay = togglePlaySpy;

      // Emulate "storage" event firing
      const event = new StorageEvent("storage", {
        key: "BrainzPlayer_stop",
        newValue: "1234567",
      });
      window.dispatchEvent(event);

      expect(togglePlaySpy).not.toHaveBeenCalled();
    });
  });

  describe("isCurrentListen", () => {
    it("returns true if currentListen and passed listen is same", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.isCurrentListen(listen)).toBe(true);
    });

    it("returns false if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: undefined });

      expect(instance.isCurrentListen({} as Listen)).toBeFalsy();
    });
  });

  describe("getCurrentTrackName", () => {
    it("returns the track name when it exists on a listen", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.getCurrentTrackName()).toEqual("Bird's Lament");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: undefined });

      expect(instance.getCurrentTrackName()).toEqual("");
    });
  });

  describe("getCurrentTrackArtists", () => {
    it("returns the track artists string when it exists on a listen", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.getCurrentTrackArtists()).toEqual("Moondog");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: undefined });

      expect(instance.getCurrentTrackArtists()).toEqual("");
    });
  });
  describe("seekToPositionMs", () => {
    it("invalidates the datasource if it doesn't exist", () => {
      const mockProps = {
        ...props,
        spotifyUser: {},
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      const fakeDatasource = {
        current: false,
      };
      instance.dataSources.push(fakeDatasource as any);

      // Setting non-existing datasource index
      const datasourcesBefore = instance.dataSources.length;
      wrapper.setState({ currentDataSourceIndex: datasourcesBefore - 1 });
      expect(
        instance.dataSources[instance.state.currentDataSourceIndex].current
      ).toEqual(false);

      instance.invalidateDataSource = jest.fn(() =>
        instance.dataSources.splice(instance.state.currentDataSourceIndex, 1)
      );
      instance.seekToPositionMs(1000);

      expect(instance.invalidateDataSource).toHaveBeenCalledTimes(1);
      expect(instance.invalidateDataSource).toHaveBeenCalledWith();
      expect(instance.dataSources).toHaveLength(datasourcesBefore - 1);
      // Check that it removed the right datasource
      instance.dataSources.forEach((dataSource) => {
        expect(dataSource.current).not.toEqual(false);
      });
    });

    it("calls seekToPositionMs on the datasource", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.invalidateDataSource = jest.fn();
      const fakeDatasource = {
        current: {
          seekToPositionMs: jest.fn(),
        },
      };
      instance.dataSources = [fakeDatasource as any];
      instance.seekToPositionMs(1000);
      expect(instance.invalidateDataSource).not.toHaveBeenCalled();
      expect(fakeDatasource.current.seekToPositionMs).toHaveBeenCalledTimes(1);
      expect(fakeDatasource.current.seekToPositionMs).toHaveBeenCalledWith(
        1000
      );
    });
  });
  describe("toggleDirection", () => {
    it("sets direction to 'down' if not set to a recognised value", () => {
      const mockProps = {
        ...props,
        direction: "" as BrainzPlayDirection,
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      expect(instance.state.direction).toEqual("down");
      instance.setState({ direction: "fnord" as BrainzPlayDirection });
      expect(instance.state.direction).toEqual("fnord");
      instance.toggleDirection();
      expect(instance.state.direction).toEqual("down");
    });

    it("alternates direction between 'up' and 'down'", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      expect(instance.state.direction).toEqual("up");
      instance.toggleDirection();
      expect(instance.state.direction).toEqual("down");
      instance.toggleDirection();
      expect(instance.state.direction).toEqual("up");
    });
  });

  describe("failedToFindTrack", () => {
    it("calls playNextTrack if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.playNextTrack = jest.fn();
      instance.failedToFindTrack();
      expect(instance.playNextTrack).toHaveBeenCalledTimes(1);
    });

    it("tries playing the current listen with the next datasource", () => {
      const mockProps = {
        ...props,
        currentListen: listen,
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.playListen = jest.fn();
      instance.failedToFindTrack();
      expect(instance.playListen).toHaveBeenCalledTimes(1);
      expect(instance.playListen).toHaveBeenCalledWith(listen, 1);
    });

    it("shows a warning if out of datasources and plays next track", () => {
      const mockProps = {
        ...props,
        currentListen: listen,
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.playNextTrack = jest.fn();
      instance.handleWarning = jest.fn();
      instance.setState({
        currentDataSourceIndex: instance.dataSources.length - 1,
      });
      instance.failedToFindTrack();
      expect(instance.playNextTrack).toHaveBeenCalledTimes(1);
      expect(instance.handleWarning).toHaveBeenCalledTimes(1);
      expect(instance.handleWarning).toHaveBeenCalledWith(
        "We couldn't find a matching song on any music service we tried",
        "Oh no !"
      );
    });
  });
});
