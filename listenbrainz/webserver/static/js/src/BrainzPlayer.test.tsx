import * as React from "react";
import { shallow, mount } from "enzyme";
import BrainzPlayer, { DataSourceType } from "./BrainzPlayer";
import YoutubePlayer from "./YoutubePlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import APIService from "./APIService";

const props = {
  spotifyUser: {
    access_token: "heyo",
    permission: "read" as SpotifyPermission,
  },
  direction: "up" as BrainzPlayDirection,
  onCurrentListenChange: (listen: Listen) => {},
  listens: [],
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => {},
  apiService: new APIService("base-uri"),
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
    const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("creates a Youtube datasource", () => {
    const mockProps = {
      ...props,
      spotifyUser: {},
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
    const instance = wrapper.instance();
    expect(instance.dataSources).toHaveLength(1);
    expect(instance.dataSources[0].current).toBeInstanceOf(YoutubePlayer);
  });

  it("creates a Spotify datasource when passed a spotify user with right permissions", () => {
    const mockProps = {
      ...props,
      spotifyUser: {
        access_token: "haveyouseenthefnords",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      },
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
    const instance = wrapper.instance();
    expect(instance.dataSources).toHaveLength(2);
    expect(instance.dataSources[0].current).toBeInstanceOf(SpotifyPlayer);
  });

  it("removes a datasource when calling invalidateDataSource", () => {
    const mockProps = {
      ...props,
      spotifyUser: {
        access_token: "haveyouseenthefnords",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      },
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
    const instance = wrapper.instance();
    instance.handleWarning = jest.fn();
    expect(instance.dataSources).toHaveLength(2);

    instance.invalidateDataSource(
      instance.dataSources[0].current as SpotifyPlayer,
      "Test message"
    );
    expect(instance.handleWarning).toHaveBeenCalledWith(
      "Test message",
      "Cannot play from this source"
    );
    expect(instance.dataSources).toHaveLength(1);
    expect(instance.dataSources[0].current).toBeInstanceOf(YoutubePlayer);
  });

  it("selects Youtube as source when listen has a youtube URL", () => {
    const mockProps = {
      ...props,
      spotifyUser: {
        access_token: "haveyouseenthefnords",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      },
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
    const instance = wrapper.instance();
    // Normally, Spotify datasource is selected by default
    expect(instance.dataSources).toHaveLength(2);
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
    const mockProps = {
      ...props,
      spotifyUser: {
        access_token: "haveyouseenthefnords",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      },
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
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
    const mockProps = {
      ...props,
      spotifyUser: {
        access_token: "haveyouseenthefnords",
        permission: "streaming user-read-email user-read-private" as SpotifyPermission,
      },
    };
    const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
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

  describe("isCurrentListen", () => {
    it("returns true if currentListen and passed listen is same", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.isCurrentListen(listen)).toBe(true);
    });

    it("returns false if currentListen is not set", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: undefined });

      expect(instance.isCurrentListen({} as Listen)).toBeFalsy();
    });
  });

  describe("getCurrentTrackName", () => {
    it("returns the track name when it exists on a listen", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.getCurrentTrackName()).toEqual("Bird's Lament");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: undefined });

      expect(instance.getCurrentTrackName()).toEqual("");
    });
  });

  describe("getCurrentTrackArtists", () => {
    it("returns the track artists string when it exists on a listen", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();

      wrapper.setProps({ currentListen: listen });

      expect(instance.getCurrentTrackArtists()).toEqual("Moondog");
    });

    it("returns an empty string if currentListen is not set", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
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
      const wrapper = mount<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
      const instance = wrapper.instance();

      expect(instance.dataSources).toHaveLength(1);
      const fakeDatasource = {
        current: false,
      };
      instance.dataSources.push(fakeDatasource as any);
      expect(instance.dataSources).toHaveLength(2);
      expect(instance.dataSources[0].current).toBeInstanceOf(YoutubePlayer);

      // Setting non-existing datasource index
      wrapper.setState({ currentDataSourceIndex: 1 });

      instance.invalidateDataSource = jest.fn(() =>
        instance.dataSources.splice(instance.state.currentDataSourceIndex, 1)
      );
      instance.seekToPositionMs(1000);

      expect(instance.invalidateDataSource).toHaveBeenCalledTimes(1);
      expect(instance.invalidateDataSource).toHaveBeenCalledWith();
      expect(instance.dataSources).toHaveLength(1);
      // Check that it removed the right datasource
      expect(instance.dataSources[0].current).toBeInstanceOf(YoutubePlayer);
    });

    it("calls seekToPositionMs on the datasource", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
      const instance = wrapper.instance();
      instance.invalidateDataSource = jest.fn();
      const fakeDatasource = {
        current: {
          seekToPositionMs: jest.fn(),
        },
      };

      instance.dataSources.push(fakeDatasource as any);
      expect(instance.dataSources).toHaveLength(3);
      wrapper.setState({ currentDataSourceIndex: 2 });

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
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
      const instance = wrapper.instance();
      expect(instance.state.direction).toEqual("down");
      instance.setState({ direction: "fnord" as BrainzPlayDirection });
      expect(instance.state.direction).toEqual("fnord");
      instance.toggleDirection();
      expect(instance.state.direction).toEqual("down");
    });

    it("alternates direction between 'up' and 'down'", () => {
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
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
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...props} />);
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
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
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
      const wrapper = shallow<BrainzPlayer>(<BrainzPlayer {...mockProps} />);
      const instance = wrapper.instance();
      instance.playNextTrack = jest.fn();
      instance.handleWarning = jest.fn();
      instance.invalidateDataSource();
      expect(instance.dataSources).toHaveLength(1);
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
