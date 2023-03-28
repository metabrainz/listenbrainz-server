import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import fetchMock from "jest-fetch-mock";
import { io } from "socket.io-client";
import { act } from "react-dom/test-utils";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIServiceClass from "../../src/utils/APIService";

import * as recentListensProps from "../__mocks__/recentListensProps.json";
import * as recentListensPropsTooManyListens from "../__mocks__/recentListensPropsTooManyListens.json";
import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "../__mocks__/recentListensPropsPlayingNow.json";

import Listens, { ListensProps, ListensState } from "../../src/user/Listens";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

// Mock socketIO library and the Socket object it returns
const mockSocket = { on: jest.fn(), emit: jest.fn() };
jest.mock("socket.io-client", () => {
  return { io: jest.fn(() => mockSocket) };
});

const {
  haveListenCount,
  latestListenTs,
  listenCount,
  listens,
  oldestListenTs,
  profileUrl,
  spotify,
  youtube,
  user,
  userPinnedRecording,
} = recentListensProps;

const props = {
  haveListenCount,
  latestListenTs,
  listenCount,
  listens,
  oldestListenTs,
  profileUrl,
  user,
  userPinnedRecording,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIServiceClass("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: { id: 1, name: "iliekcomputers", auth_token: "fnord" },
  },
};

const propsOneListen = {
  ...recentListensPropsOneListen,
  newAlert: () => {},
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);
describe("Listens page", () => {
  it("renders correctly on the profile page", () => {
    // Datepicker component uses current time at load as max date,
    // and PinnedRecordingModal component uses current time at load to display recording unpin date,
    // so we have to mock the Date constructor otherwise snapshots will be different every day
    const mockDate = new Date("2021-05-19");
    const fakeDateNow = jest
      .spyOn(global.Date, "now")
      .mockImplementation(() => mockDate.getTime());

    // eslint-disable-next-line no-import-assign
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = mount<Listens>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <Listens {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
  });

  describe("componentDidMount", () => {
    it("calls connectWebsockets", () => {
      const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
      const instance = wrapper.instance();
      instance.connectWebsockets = jest.fn();

      act(() => {
        instance.componentDidMount();
      });

      expect(instance.connectWebsockets).toHaveBeenCalledTimes(1);
    });

    it("calls getUserListenCount", async () => {
      const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
      const instance = wrapper.instance();

      const spy = jest.fn().mockImplementation(() => {
        return Promise.resolve(42);
      });
      instance.context.APIService.getUserListenCount = spy;
      expect(wrapper.state("listenCount")).toBeUndefined();
      await act(async () => {
        await instance.componentDidMount();
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledWith(user.name);
      expect(wrapper.state("listenCount")).toEqual(42);
    });

    it("calls loadFeedback if user is logged in", () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Listens {...propsOneListen} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.loadFeedback = jest.fn();

      act(() => {
        instance.componentDidMount();
      });

      expect(instance.loadFeedback).toHaveBeenCalledTimes(1);
    });

    it('does not fetch user feedback if user is not logged in"', () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider
          value={{
            ...mountOptions.context,
            currentUser: {} as ListenBrainzUser,
          }}
        >
          <Listens {...propsOneListen} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const loadFeedbackSpy = jest.spyOn(instance, "loadFeedback");
      const APIFeedbackSpy = jest.spyOn(
        instance.context.APIService,
        "getFeedbackForUserForRecordings"
      );
      act(() => {
        instance.componentDidMount();
      });

      expect(loadFeedbackSpy).toHaveBeenCalledTimes(1);
      expect(APIFeedbackSpy).not.toHaveBeenCalled();
    });
  });

  describe("createWebsocketsConnection", () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });
    it("calls io with correct parameters", () => {
      const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
      const instance = wrapper.instance();
      act(() => {
        instance.createWebsocketsConnection();
      });

      expect(io).toHaveBeenCalled();

      expect(mockSocket.on).toHaveBeenNthCalledWith(
        1,
        "connect",
        expect.any(Function)
      );
      expect(mockSocket.on).toHaveBeenNthCalledWith(
        2,
        "listen",
        expect.any(Function)
      );
      expect(mockSocket.on).toHaveBeenNthCalledWith(
        3,
        "playing_now",
        expect.any(Function)
      );
    });
  });

  describe("addWebsocketsHandlers", () => {
    it('calls correct handler for "listen" event', () => {
      const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
      const instance = wrapper.instance();

      // eslint-disable-next-line dot-notation
      const spy = jest.spyOn(instance["socket"], "on");
      spy.mockImplementation(
        // @ts-ignore
        (event: string, listener: (...args: any[]) => void): any => {
          if (event === "listen") {
            listener(JSON.stringify(recentListensPropsOneListen.listens[0]));
          }
        }
      );
      instance.receiveNewListen = jest.fn();
      act(() => {
        instance.addWebsocketsHandlers();
      });

      expect(instance.receiveNewListen).toHaveBeenCalledWith(
        JSON.stringify(recentListensPropsOneListen.listens[0])
      );
      spy.mockReset();
    });

    it('calls correct event for "playing_now" event', () => {
      const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
      const instance = wrapper.instance();

      // eslint-disable-next-line dot-notation
      const spy = jest.spyOn(instance["socket"], "on");
      spy.mockImplementation((event, fn: any): any => {
        if (event === "playing_now") {
          fn(JSON.stringify(recentListensPropsPlayingNow.listens[0]));
        }
      });
      instance.receiveNewPlayingNow = jest.fn();
      act(() => {
        instance.addWebsocketsHandlers();
      });

      expect(instance.receiveNewPlayingNow).toHaveBeenCalledWith(
        recentListensPropsPlayingNow.listens[0]
      );
      spy.mockReset();
    });
  });

  describe("receiveNewListen", () => {
    const mockListen: Listen = {
      track_metadata: {
        artist_name: "Coldplay",
        track_name: "Viva La Vida",
        additional_info: {
          recording_msid: "2edee875-55c3-4dad-b3ea-e8741484f4b5",
        },
      },
      listened_at: 1586580524,
      listened_at_iso: "2020-04-10T10:12:04Z",
    };
    it("crops the listens array if length is more than or equal to 100", async () => {
      /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
       * so that it doesn't get passed as a reference.
       */
      const wrapper = mount<Listens>(
        <Listens
          {...(JSON.parse(
            JSON.stringify(recentListensPropsTooManyListens)
          ) as ListensProps)}
          newAlert={jest.fn()}
        />,
        mountOptions
      );
      const instance = wrapper.instance();

      await act(() => {
        instance.receiveNewListen(JSON.stringify(mockListen));
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("listens").length).toBeLessThanOrEqual(100);

      /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
       * so that it doesn't get passed as a reference.
       */
      await act(() => {
        wrapper.setState({
          listens: JSON.parse(
            JSON.stringify(recentListensPropsTooManyListens.listens)
          ),
        });
      });
      await act(() => {
        instance.receiveNewListen(JSON.stringify(mockListen));
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("listens").length).toBeLessThanOrEqual(100);
    });

    it("inserts the received listen for other modes", async () => {
      /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
       * so that it doesn't get passed as a reference.
       */
      const wrapper = mount<Listens>(
        <Listens {...propsOneListen} />,
        mountOptions
      );
      const instance = wrapper.instance();
      const result: Array<Listen> = Array.from(
        recentListensPropsOneListen.listens
      );
      result.unshift(mockListen);
      await act(() => {
        instance.receiveNewListen(JSON.stringify(mockListen));
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("listens")).toHaveLength(result.length);
      expect(wrapper.state("listens")).toEqual(result);
    });
  });

  describe("receiveNewPlayingNow", () => {
    const mockListenOne: Listen = {
      track_metadata: {
        artist_name: "Coldplay",
        track_name: "Viva La Vida",
      },
      playing_now: true,
      user_name: "ishaanshah",
      listened_at: 1586580524,
      listened_at_iso: "2020-04-10T10:12:04Z",
    };

    it("sets state correctly for other modes", async () => {
      const spy = jest
        .spyOn(mountOptions.context.APIService, "lookupRecordingMetadata")
        .mockImplementation(() => Promise.resolve(null));
      /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
       * so that it doesn't get passed as a reference.
       */
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Listens
            {...(JSON.parse(
              JSON.stringify(recentListensPropsPlayingNow)
            ) as ListensProps)}
            newAlert={jest.fn()}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
       * so that it doesn't get passed as a reference.
       */
      const result = JSON.parse(
        JSON.stringify(recentListensPropsPlayingNow.listens)
      );
      // listens with playing_now gets removed from listens and save in playingNowListen
      const firstPlayingNow = result.shift();
      expect(wrapper.state("listens")).toEqual(result);
      expect(wrapper.state("playingNowListen")).toEqual(firstPlayingNow);

      await act(async () => {
        await instance.receiveNewPlayingNow(mockListenOne);
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("listens")).toEqual(result);
      expect(wrapper.state("playingNowListen")).toEqual(mockListenOne);
      spy.mockRestore();
    });
  });

  describe("deleteListen", () => {
    it("calls API and removeListenFromListenList correctly, and updates the state", async () => {
      const newAlertMock = jest.fn();
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Listens {...props} newAlert={newAlertMock} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      expect(instance.context.currentUser.name).toEqual("iliekcomputers");
      const spy = jest
        .spyOn(instance.context.APIService, "deleteListen")
        .mockImplementation(() => Promise.resolve(200));
      const removeListenCallbackSpy = jest.spyOn(
        instance,
        "removeListenFromListenList"
      );

      const listenToDelete = props.listens[0];
      await act(async () => {
        await instance.deleteListen(listenToDelete);
      });
      await waitForComponentToPaint(wrapper, 1000);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "fnord",
        "973e5620-829d-46dd-89a8-760d87076287",
        1586523524
      );

      expect(removeListenCallbackSpy).toHaveBeenCalledTimes(1);
      expect(removeListenCallbackSpy).toHaveBeenCalledWith(listenToDelete);
      expect(instance.state.deletedListen).toEqual(listenToDelete);
      expect(instance.state.listens).not.toContainEqual(listenToDelete);
      expect(newAlertMock).toHaveBeenCalledWith(
        "info",
        "Success",
        "This listen has not been deleted yet, but is scheduled for deletion," +
          " which usually happens shortly after the hour."
      );
    });

    it("does nothing if isCurrentUser is false", async () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider
          value={{
            ...mountOptions.context,
            currentUser: {} as ListenBrainzUser,
          }}
        >
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(instance.state.deletedListen).toEqual(null);
      const listenToDelete = props.listens[0];
      await act(async () => {
        await instance.deleteListen(listenToDelete);
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(0);
      expect(instance.state.deletedListen).toEqual(null);
    });

    it("does not render delete listen control if isCurrentUser is false", async () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider
          value={{
            ...mountOptions.context,
            currentUser: {} as ListenBrainzUser,
          }}
        >
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );
      expect(wrapper.find("button[title='Delete Listen']")).toHaveLength(0);
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider
          value={{
            ...mountOptions.context,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(instance.state.deletedListen).toEqual(null);
      const listenToDelete = props.listens[0];
      await act(async () => {
        await instance.deleteListen(listenToDelete);
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(0);
      expect(instance.state.deletedListen).toEqual(null);
    });

    it("doesn't call removeListenFromListenList or update state if status code is not 200", async () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const removeListenCallbackSpy = jest.spyOn(
        instance,
        "removeListenFromListenList"
      );

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(500));

      const listenToDelete = props.listens[0];
      await act(async () => {
        await instance.deleteListen(listenToDelete);
      });
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "fnord",
        "973e5620-829d-46dd-89a8-760d87076287",
        1586523524
      );

      expect(removeListenCallbackSpy).toHaveBeenCalledTimes(0);
      expect(instance.state.listens).toContainEqual(listenToDelete);
    });

    it("calls newAlert if error is returned", async () => {
      const newAlertMock = jest.fn();
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Listens {...props} newAlert={newAlertMock} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const error = new Error("my error message");
      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => {
        throw error;
      });

      const listenToDelete = props.listens[0];
      await act(async () => {
        await instance.deleteListen(listenToDelete);
      });
      await waitForComponentToPaint(wrapper);

      expect(newAlertMock).toHaveBeenCalledWith(
        "danger",
        "Error while deleting listen",
        "my error message"
      );
    });
  });

  describe("Pagination", () => {
    const pushStateSpy = jest.spyOn(window.history, "pushState");

    afterEach(() => {
      jest.clearAllMocks();
    });

    describe("handleClickOlder", () => {
      it("does nothing if there is no older listens timestamp", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ nextListenTs: undefined });
        });
        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickOlder();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get older listens", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ nextListenTs: 1586450000 });
        });
        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 1586450001,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedListensArray));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickOlder();
        });
        await waitForComponentToPaint(wrapper);

        expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586450000);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("listens")).toEqual(expectedListensArray);
      });

      it("sets nextListenTs to undefined if it receives no listens from API", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ nextListenTs: 1586450000 });
        });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickOlder();
        });
        await waitForComponentToPaint(wrapper);

        expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586450000);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toBeUndefined();
        expect(pushStateSpy).not.toHaveBeenCalled();
      });

      it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();

        await act(() => {
          // Random nextListenTs to ensure that is the value set in browser history
          wrapper.setProps({ latestListenTs: 1586623524 });
          wrapper.setState({ listens: [], nextListenTs: 1586440600 });
        });

        const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
          return Promise.resolve(listens);
        });
        instance.context.APIService.getListensForUser = spy;
        const scrollSpy = jest.spyOn(instance, "afterListensFetch");

        await act(() => {
          instance.handleClickOlder();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("listens")).toEqual(listens);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toEqual(
          listens[listens.length - 1].listened_at
        );
        expect(wrapper.state("previousListenTs")).toEqual(
          listens[0].listened_at
        );
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          `?max_ts=1586440600`
        );
        expect(scrollSpy).toHaveBeenCalled();
        expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586440600);
      });

      it("disables 'next' pagination if returned less listens than expected", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />);
        await act(() => {
          wrapper.setState({ nextListenTs: 1586440539 });
        });
        const instance = wrapper.instance();

        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 1586450001,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedListensArray));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getListensForUser = spy;
        instance.getFeedback = jest.fn();

        await act(() => {
          instance.handleClickOlder();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toBeUndefined();
        expect(wrapper.state("previousListenTs")).toEqual(1586450001);
        expect(wrapper.state("listens")).toEqual(expectedListensArray);
        expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586440539);
      });
    });

    describe("handleClickNewer", () => {
      it("does nothing if there is no newer listens timestamp", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ previousListenTs: undefined });
        });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickNewer();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("calls the API to get older listens", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ previousListenTs: 123456 });
        });

        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 1586450001,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedListensArray));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickNewer();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("listens")).toEqual(expectedListensArray);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).toHaveBeenCalledWith(user.name, 123456, undefined);
      });

      it("sets nextListenTs to undefined if it receives no listens from API", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ previousListenTs: 123456 });
        });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickNewer();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("previousListenTs")).toBeUndefined();
        expect(pushStateSpy).not.toHaveBeenCalled();
      });

      it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setProps({ latestListenTs: 1586623524 });
          wrapper.setState({ previousListenTs: 123456 });
        });

        const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
          return Promise.resolve(listens);
        });
        instance.context.APIService.getListensForUser = spy;
        const scrollSpy = jest.spyOn(instance, "afterListensFetch");

        await act(() => {
          instance.handleClickNewer();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("listens")).toEqual(listens);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toEqual(
          listens[listens.length - 1].listened_at
        );

        expect(wrapper.state("previousListenTs")).toEqual(
          listens[0].listened_at
        );
        expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?min_ts=123456`);
        expect(scrollSpy).toHaveBeenCalled();
      });
      it("disables pagination if returned less listens than expected", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({ previousListenTs: 123456 });
        });

        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 1586450001,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(expectedListensArray));
        // eslint-disable-next-line dot-notation
        instance["APIService"].getListensForUser = spy;

        await act(() => {
          instance.handleClickNewer();
        });
        await waitForComponentToPaint(wrapper);

        expect(wrapper.state("listens")).toEqual(expectedListensArray);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toBeUndefined();
        expect(wrapper.state("previousListenTs")).toBeUndefined();
        expect(spy).toHaveBeenCalledWith(user.name, 123456, undefined);
      });
    });

    describe("handleClickOldest", () => {
      it("does nothing if last listens is the oldest", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({
            listens: [
              {
                track_metadata: {
                  artist_name: "Beyonc\u00e9, Frank Ocean",
                  track_name: "Superpower (feat. Frank Ocean)",
                  release_name: "BEYONC\u00c9 [Platinum Edition]",
                },
                listened_at: 123456,
              },
            ],
          });
          wrapper.setProps({ oldestListenTs: 123456 });
        });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickOldest();
        });
        await waitForComponentToPaint(wrapper);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
        const listen = {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 1586440600,
        };
        const extraProps = { ...props, listens: [listen] };
        const wrapper = mount<Listens>(
          <Listens {...extraProps} />,
          mountOptions
        );

        const instance = wrapper.instance();

        const oldestlisten = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 1586440536,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(oldestlisten));
        instance.context.APIService.getListensForUser = spy;
        const scrollSpy = jest.spyOn(instance, "afterListensFetch");

        await act(() => {
          instance.handleClickOldest();
        });
        await waitForComponentToPaint(wrapper);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).toHaveBeenCalledWith(user.name, 1586440535);
        expect(wrapper.state("listens")).toEqual(oldestlisten);
        expect(wrapper.state("nextListenTs")).toEqual(undefined);
        expect(wrapper.state("previousListenTs")).toEqual(1586440536);
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          `?min_ts=1586440535`
        );
        expect(scrollSpy).toHaveBeenCalled();
      });
    });

    describe("handleClickNewest", () => {
      it("does nothing if first listens is the newest", async () => {
        const wrapper = mount<Listens>(<Listens {...props} />, mountOptions);
        const instance = wrapper.instance();
        await act(() => {
          wrapper.setState({
            listens: [
              {
                track_metadata: {
                  artist_name: "Beyonc\u00e9, Frank Ocean",
                  track_name: "Superpower (feat. Frank Ocean)",
                  release_name: "BEYONC\u00c9 [Platinum Edition]",
                },
                listened_at: 123456,
              },
            ],
          });
          wrapper.setProps({ latestListenTs: 123456 });
        });

        const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
        instance.context.APIService.getListensForUser = spy;

        await act(() => {
          instance.handleClickNewest();
        });
        await waitForComponentToPaint(wrapper);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(spy).not.toHaveBeenCalled();
      });

      it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
        const listen = {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 123450,
        };
        const extraProps = { ...props, listens: [listen] };
        const wrapper = mount<Listens>(
          <Listens {...extraProps} />,
          mountOptions
        );
        await act(() => {
          wrapper.setProps({ latestListenTs: 123456 });
        });
        const instance = wrapper.instance();

        const newestListen = [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 123456,
          },
        ];
        const spy = jest
          .fn()
          .mockImplementation(() => Promise.resolve(newestListen));
        instance.context.APIService.getListensForUser = spy;
        const scrollSpy = jest.spyOn(instance, "afterListensFetch");
        await act(() => {
          instance.handleClickNewest();
        });
        await waitForComponentToPaint(wrapper);
        expect(spy).toHaveBeenCalledWith(user.name);
        expect(wrapper.state("listens")).toEqual(newestListen);
        expect(wrapper.state("loading")).toBeFalsy();
        expect(wrapper.state("nextListenTs")).toEqual(undefined);
        expect(wrapper.state("previousListenTs")).toEqual(undefined);
        expect(pushStateSpy).toHaveBeenCalledWith(null, "", "");
        expect(scrollSpy).toHaveBeenCalled();
      });
    });
  });
});

/* eslint-enable jest/no-disabled-tests */
