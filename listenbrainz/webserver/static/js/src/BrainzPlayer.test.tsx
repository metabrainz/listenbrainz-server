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
  listens: [],
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => {},
  refreshSpotifyToken: jest.fn(),
  refreshYoutubeToken: jest.fn(),
};
const spotifyAccountWithPermissions = {
  access_token: "haveyouseenthefnords",
  permission: ["streaming", "user-read-email", "user-read-private"] as Array<
    SpotifyPermission
  >,
};

const GlobalContextMock = {
  context: {
    APIBaseURI: "base-uri",
    APIService: new APIService("base-uri"),
    spotifyAuth: {
      access_token: "heyo",
      permission: [
        "user-read-currently-playing",
        "user-read-recently-played",
      ] as Array<SpotifyPermission>,
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
// On the other hand, do yourself a favor and *do not* go listen to this one
const listen2: Listen = {
  listened_at: 42,
  track_metadata: {
    artist_name: "Rick Astley",
    track_name: "Never Gonna Give You Up",
  },
};

describe("BrainzPlayer", () => {
  beforeAll(() => {
    // delete window.location;
    window.location = {
      href: "http://nevergonnagiveyouup.com",
    } as Window["location"];
  });

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
    // Make spotify last source in array
    instance.dataSources.splice(2, 0, ...instance.dataSources.splice(0, 1));
    expect(instance.dataSources[2].current).toBeInstanceOf(SpotifyPlayer);
    // Try to play, should select spotify instead of first in list
    expect(instance.state.currentDataSourceIndex).toEqual(0);
    instance.playListen(spotifyListen);
    expect(instance.state.currentDataSourceIndex).toEqual(2);
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
    // Make spotify last source in array
    instance.dataSources.splice(2, 0, ...instance.dataSources.splice(0, 1));
    expect(instance.dataSources[2].current).toBeInstanceOf(SpotifyPlayer);
    // Try to play, should select spotify instead of first in list
    expect(instance.state.currentDataSourceIndex).toEqual(0);
    instance.playListen(spotifyListen);
    expect(instance.state.currentDataSourceIndex).toEqual(2);
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

  describe("isCurrentlyPlaying", () => {
    it("returns true if currentListen and passed listen is same", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setState({ currentListen: listen });

      expect(instance.isCurrentlyPlaying(listen)).toBe(true);
    });

    it("returns false if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setState({ currentListen: undefined });

      expect(instance.isCurrentlyPlaying({} as Listen)).toBeFalsy();
    });
  });

  describe("getCurrentTrackName", () => {
    it("returns the track name when it exists on a listen", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setState({ currentListen: listen });

      expect(instance.getCurrentTrackName()).toEqual("Bird's Lament");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setState({ currentListen: undefined });

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

      wrapper.setState({ currentListen: listen });

      expect(instance.getCurrentTrackArtists()).toEqual("Moondog");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();

      wrapper.setState({ currentListen: undefined });

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
        current: undefined,
      };

      // Setting fake datasource as curently used datasource
      instance.dataSources.push(fakeDatasource as any);
      const numberOfDatasourcesBefore = instance.dataSources.length;
      wrapper.setState({
        currentDataSourceIndex: numberOfDatasourcesBefore - 1,
        isActivated: true,
      });
      // Ensure we have the right datasource selected
      expect(
        instance.dataSources[instance.state.currentDataSourceIndex]
      ).toEqual(fakeDatasource);

      const invalidateDataSourceSpy = jest.spyOn(
        instance,
        "invalidateDataSource"
      );
      instance.seekToPositionMs(1000);

      expect(invalidateDataSourceSpy).toHaveBeenCalledTimes(1);
      expect(invalidateDataSourceSpy).toHaveBeenCalledWith();
      expect(instance.dataSources).toHaveLength(numberOfDatasourcesBefore - 1);
      // Ensure it removed the right datasource
      instance.dataSources.forEach((dataSource) => {
        expect(dataSource).not.toEqual(fakeDatasource);
      });
    });

    it("calls seekToPositionMs on the datasource", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      wrapper.setState({ isActivated: true });
      instance.invalidateDataSource = jest.fn();
      const fakeDatasource = {
        current: {
          seekToPositionMs: jest.fn(),
          canSearchAndPlayTracks() {
            return true;
          },
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

  describe("failedToPlayTrack", () => {
    it("does nothing if isActivated is false", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.playNextTrack = jest.fn();
      instance.failedToPlayTrack();
      expect(instance.playNextTrack).not.toHaveBeenCalled();
    });

    it("tries to play the next track if currentListen is not set", () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      wrapper.setState({ isActivated: true });
      instance.playNextTrack = jest.fn();
      instance.failedToPlayTrack();
      expect(instance.playNextTrack).toHaveBeenCalledTimes(1);
    });

    it("tries playing the current listen with the next datasource", () => {
      const mockProps = {
        ...props,
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      wrapper.setState({ isActivated: true, currentListen: listen });
      instance.playNextTrack = jest.fn();
      instance.playListen = jest.fn();
      instance.failedToPlayTrack();
      expect(instance.playNextTrack).not.toHaveBeenCalled();
      expect(instance.playListen).toHaveBeenCalledWith(listen, 1);
    });

    it("calls playNextTrack if we ran out of datasources", () => {
      const mockProps = {
        ...props,
        listens: [listen2, listen],
      };
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...mockProps} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      wrapper.setState({
        isActivated: true,
        currentDataSourceIndex: instance.dataSources.length - 1,
        currentListen: listen,
      });
      const playNextTrackSpy = jest.spyOn(instance, "playNextTrack");
      instance.playListen = jest.fn();
      instance.handleWarning = jest.fn();
      instance.failedToPlayTrack();
      expect(instance.handleWarning).not.toHaveBeenCalled();
      expect(playNextTrackSpy).toHaveBeenCalledTimes(1);
      expect(instance.playListen).toHaveBeenCalledTimes(1);
      expect(instance.playListen).toHaveBeenCalledWith(listen2);
    });
  });
  describe("submitListenToListenBrainz", () => {
    const trackInfo = {
      title: "Never Gonna Give You Up",
      artist: "Rick Astley",
      trackURL: "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
    };
    beforeAll(() => {
      jest.useFakeTimers();
    });
    afterAll(() => {
      jest.useRealTimers();
    });
    it("does nothing if user is not logged in", async () => {
      const wrapper = mount<BrainzPlayer>(
        <BrainzPlayer {...props} />,
        GlobalContextMock
      );
      const instance = wrapper.instance();
      instance.playNextTrack = jest.fn();
      const ds =
        instance.dataSources[instance.state.currentDataSourceIndex].current;
      const dsRecordsListens = ds && jest.spyOn(ds, "datasourceRecordsListens");
      await instance.submitListenToListenBrainz("single", listen);
      expect(dsRecordsListens).not.toHaveBeenCalled();
    });

    it("does nothing if datasource already submits listens", async () => {
      const wrapper = mount<BrainzPlayer>(
        <GlobalAppContext.Provider
          value={{
            ...GlobalContextMock.context,
            // These permissions suggest LB records listens and can play using BrainzPlayer
            spotifyAuth: {
              access_token: "merde-à-celui-qui-lit",
              permission: [
                "streaming",
                "user-read-email",
                "user-read-private",
                "user-read-currently-playing",
                "user-read-recently-played",
              ],
            },
            currentUser: {
              name: "Gulab Jamun",
              auth_token: "IHaveSeenTheFnords",
            },
          }}
        >
          <BrainzPlayer {...props} listens={[listen2]} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const ds = instance.dataSources[instance.state.currentDataSourceIndex]
        ?.current as DataSourceType;
      expect(ds).toBeDefined();
      expect(ds).toBeInstanceOf(SpotifyPlayer);
      // GlobalContextMock.spotifyAuth includes permissions suggesting LB records Spotify listens already
      expect(ds.datasourceRecordsListens()).toBeTruthy();
      const submitListensAPISpy = jest.spyOn(
        instance.context.APIService,
        "submitListens"
      );
      await instance.submitListenToListenBrainz("single", listen);
      expect(submitListensAPISpy).not.toHaveBeenCalled();
    });

    it("submits a playing_now with the expected metadata", async () => {
      const dateNowMock = jest.fn().mockReturnValue(1234567890);
      Date.now = dateNowMock;
      const wrapper = mount<BrainzPlayer>(
        <GlobalAppContext.Provider
          value={{
            ...GlobalContextMock.context,
            // These permissions suggest LB does *not* record listens
            spotifyAuth: spotifyAccountWithPermissions,
            currentUser: {
              name: "Gulab Jamun",
              auth_token: "IHaveSeenTheFnords",
            },
          }}
        >
          <BrainzPlayer {...props} listens={[listen2]} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.setState({
        currentListen: listen2,
        currentTrackName: "Never Gonna Give You Up",
        currentTrackArtist: "Rick Astley",
        currentTrackURL:
          "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
      });

      const ds = instance.dataSources[instance.state.currentDataSourceIndex]
        ?.current as DataSourceType;
      expect(ds).toBeDefined();
      expect(ds).toBeInstanceOf(SpotifyPlayer);
      expect(ds.datasourceRecordsListens()).toBeFalsy();

      const submitListensAPISpy = jest.spyOn(
        instance.context.APIService,
        "submitListens"
      );
      await instance.submitNowPlayingToListenBrainz();
      const expectedListen = {
        listened_at: 1234567,
        track_metadata: {
          artist_name: "Rick Astley",
          track_name: "Never Gonna Give You Up",
          additional_info: {
            media_player: "BrainzPlayer",
            submission_client: "BrainzPlayer",
            music_service: "https://open.spotify.com",
            origin_url: "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            brainzplayer_metadata: {
              artist_name: "Rick Astley",
              release_name: undefined,
              track_name: "Never Gonna Give You Up",
            },
          },
        },
      };
      expect(submitListensAPISpy).toHaveBeenCalledTimes(1);
      expect(submitListensAPISpy).toHaveBeenCalledWith(
        "IHaveSeenTheFnords",
        "playing_now",
        [expectedListen]
      );
    });

    it("submits a full listen after 30s with the expected metadata", async () => {
      const dateNowMock = jest.fn().mockReturnValue(1234567890);
      Date.now = dateNowMock;

      const wrapper = mount<BrainzPlayer>(
        <GlobalAppContext.Provider
          value={{
            ...GlobalContextMock.context,
            // These permissions suggest LB does *not* record listens
            spotifyAuth: spotifyAccountWithPermissions,
            currentUser: {
              name: "Gulab Jamun",
              auth_token: "IHaveSeenTheFnords",
            },
          }}
        >
          <BrainzPlayer {...props} listens={[listen2]} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      instance.setState({
        currentListen: listen2,
        currentTrackName: "Never Gonna Give You Up",
        currentTrackArtist: "Rick Astley",
        currentTrackURL:
          "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
        continuousPlaybackTime: 15000,
        durationMs: 123990,
      });

      const ds = instance.dataSources[instance.state.currentDataSourceIndex]
        ?.current as DataSourceType;
      expect(ds).toBeDefined();
      expect(ds).toBeInstanceOf(SpotifyPlayer);
      expect(ds.datasourceRecordsListens()).toBeFalsy();

      const submitListensAPISpy = jest.spyOn(
        instance.context.APIService,
        "submitListens"
      );
      const expectedListen = {
        listened_at: 1234567,
        track_metadata: {
          artist_name: "Rick Astley",
          track_name: "Never Gonna Give You Up",
          additional_info: {
            media_player: "BrainzPlayer",
            submission_client: "BrainzPlayer",
            music_service: "https://open.spotify.com",
            origin_url: "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            brainzplayer_metadata: {
              artist_name: "Rick Astley",
              release_name: undefined,
              track_name: "Never Gonna Give You Up",
            },
          },
        },
      };
      // After 15 seconds
      await instance.checkProgressAndSubmitListen();
      expect(submitListensAPISpy).not.toHaveBeenCalled();
      // And now after 30 seconds
      instance.setState({ continuousPlaybackTime: 30001 });
      await instance.checkProgressAndSubmitListen();
      expect(submitListensAPISpy).toHaveBeenCalledTimes(1);
      expect(submitListensAPISpy).toHaveBeenLastCalledWith(
        "IHaveSeenTheFnords",
        "single",
        [expectedListen]
      );
    });
  });
});
