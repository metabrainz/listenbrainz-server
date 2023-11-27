/* eslint-disable testing-library/no-unnecessary-act */
import * as React from "react";

import {
  screen,
  within,
  act,
  waitFor,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import fetchMock from "jest-fetch-mock";
import WS from "jest-websocket-mock";
import { SocketIO as mockSocketIO } from "mock-socket";
import userEvent from "@testing-library/user-event";
import type { UserEvent } from "@testing-library/user-event/dist/types/setup/setup";
import APIServiceClass from "../../src/utils/APIService";

import * as recentListensProps from "../__mocks__/recentListensProps.json";
import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "../__mocks__/recentListensPropsPlayingNow.json";
import Listens, { ListensProps } from "../../src/user/Listens";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

jest.mock("socket.io-client", () => ({
  ...mockSocketIO,
  io: mockSocketIO.connect,
}));

jest.unmock("react-toastify");
// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  userPinnedRecording,
} = recentListensProps;

const props: ListensProps = {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  userPinnedRecording,
};

const APIService = new APIServiceClass("foo");
const currentUser = { id: 1, name: "iliekcomputers", auth_token: "fnord" };

const propsOneListen = {
  ...recentListensPropsOneListen,
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("Listens page", () => {
  jest.setTimeout(10000);

  let userEventSession: UserEvent;
  beforeAll(async () => {
    userEventSession = await userEvent.setup();
  });

  it("renders correctly on the profile page", async () => {
    /* eslint-disable testing-library/prefer-screen-queries */
    const { findByTestId, getAllByTestId } = renderWithProviders(
      <Listens {...props} />,
      { APIService, currentUser }
    );
    await findByTestId("listens");
    // 25 listens + one pinned recording listen
    expect(getAllByTestId("listen")).toHaveLength(26);
    /* eslint-enable testing-library/prefer-screen-queries */
  });

  it("fetches the user's listen count", async () => {
    const spy = jest.fn().mockImplementation(() => {
      return Promise.resolve(42);
    });
    APIService.getUserListenCount = spy;

    await act(async () => {
      renderWithProviders(<Listens {...props} />, { APIService, currentUser });
    });

    const listenCountCard = await screen.findByTestId("listen-count-card");
    // Due to the rendering of the card, the text representation appears with missing spaces
    expect(listenCountCard).toHaveTextContent(
      "You have listened to42songs so far"
    );
    expect(spy).toHaveBeenCalledWith(user.name);
  });

  describe("websocket features", () => {
    const mockListen: Listen = {
      track_metadata: {
        artist_name: "FNORD",
        track_name: "Have you seen the FNORDs?",
        additional_info: {
          recording_msid: "a6a0d9da-475b-45cb-a5a8-087caa1a121a",
        },
      },
      listened_at: Date.now(),
      listened_at_iso: "2020-04-10T10:12:04Z",
      user_name: "mr_monkey",
      playing_now: true,
    };
    let websocketServer: WS;

    beforeEach(() => {
      websocketServer = new WS("http://localhost");
      // Leaving these commented out for easier debugging
      // websocketServer.on("connection", (server) => {
      //   console.log("onconnection", server);
      // });
      // websocketServer.on("message", (x) => {
      //   console.log("onmessage", x);
      // });
      // websocketServer.on("close", (server) => {
      //   console.log("onclose", server);
      // });
      // websocketServer.on("json", (server) => {
      //   console.log("received 'json' type message", server);
      // });
    });

    afterEach(() => {
      WS.clean();
    });

    it("sets up a websocket connection with correct parameters", async () => {
      let receivedUserNameMessage = false;
      // Connection message from the client to the server
      // Cannot currently test this with "expect(…).toReceiveMessage" with mock-socket
      // because contrarily to socket.io it does not allow arbitrary types of messages
      // in our case socket.emit("json",{user:username}) message type
      const returnPromise = new Promise<void>((resolve, reject) => {
        // @ts-ignore
        websocketServer.on("json", (userJson) => {
          try {
            expect(userJson).toEqual({ user: "iliekcomputers" });
            receivedUserNameMessage = true;
            resolve();
          } catch (error) {
            reject(error);
          }
        });
      });
      await act(async () => {
        renderWithProviders(<Listens {...props} />);
      });
      await websocketServer.connected;
      await returnPromise; // See at the beginning of this test

      const websocketClients = websocketServer.server.clients();
      expect(websocketClients.length).toBeGreaterThanOrEqual(1);
      expect(receivedUserNameMessage).toBeTruthy();
    });

    it('calls correct handler for "listen" event', async () => {
      await act(async () => {
        renderWithProviders(<Listens {...props} />);
      });
      await websocketServer.connected;

      expect(screen.queryByTestId("webSocketListens")).not.toBeInTheDocument();
      expect(screen.queryAllByTestId("listen")).toHaveLength(26);
      // send the message to the client

      await act(async () => {
        websocketServer.server.emit("listen", JSON.stringify(mockListen));
      });
      const websocketListensContainer = await screen.findByTestId(
        "webSocketListens",
        {}
      );
      const wsListens = within(websocketListensContainer).queryAllByTestId(
        "listen"
      );
      expect(wsListens).toHaveLength(1);
      expect(screen.queryAllByTestId("listen")).toHaveLength(27);
    });

    it('calls correct event for "playing_now" event', async () => {
      await act(async () => {
        renderWithProviders(<Listens {...props} />);
      });
      await websocketServer.connected;
      expect(screen.queryAllByTestId("listen")).toHaveLength(26);

      const playingNowListen: Listen = {
        ...mockListen,
        listened_at: Date.now(),
        playing_now: true,
      };

      await act(async () => {
        websocketServer.server.emit(
          "playing_now",
          JSON.stringify(playingNowListen)
        );
      });
      const listenCards = screen.queryAllByTestId("listen");
      expect(listenCards).toHaveLength(27);
      await screen.findByTitle(playingNowListen.track_metadata.track_name, {});
    });

    it("crops the websocket listens array to a maximum of 7", async () => {
      await act(async () => {
        renderWithProviders(<Listens {...props} />);
      });
      await websocketServer.connected;

      // Add 7 new listens
      await act(async () => {
        for (let index = 0; index < 8; index += 1) {
          // Prevent the "Encountered two children with the same key" warning message
          // by having a different timestamp for each listen
          websocketServer.server.emit(
            "listen",
            JSON.stringify({ ...mockListen, listened_at: Date.now() + index })
          );
        }
      });

      const websocketListensContainer = await screen.findByTestId(
        "webSocketListens"
      );
      const wsListens = within(websocketListensContainer).queryAllByTestId(
        "listen"
      );
      expect(wsListens).toHaveLength(7);

      // Add a few more, the process should crop to 7 max
      await act(async () => {
        websocketServer.server.emit(
          "listen",
          JSON.stringify({ ...mockListen, listened_at: Date.now() })
        );
      });
      await act(async () => {
        websocketServer.server.emit(
          "listen",
          JSON.stringify({ ...mockListen, listened_at: Date.now() })
        );
      });
      await act(async () => {
        websocketServer.server.emit(
          "listen",
          JSON.stringify({ ...mockListen, listened_at: Date.now() })
        );
      });

      // Should still have 7 listens
      expect(wsListens).toHaveLength(7);
    });
  });

  describe("deleteListen", () => {
    it("calls API and removeListenFromListenList correctly, and updates the state", async () => {
      const spy = jest
        .spyOn(APIService, "deleteListen")
        .mockImplementation(() => Promise.resolve(200));

      await act(async () => {
        renderWithProviders(<Listens {...props} />, {
          APIService,
          currentUser,
        });
      });

      expect(await screen.findAllByTestId("listen")).toHaveLength(26);

      const listensContainer = await screen.findByTestId("listens");
      const listenCards = await within(listensContainer).findAllByTestId(
        "listen"
      );
      const listenToDelete = listenCards[0];

      const deleteButton = within(listenToDelete).getByRole("menuitem", {
        name: "Delete Listen",
      });
      await userEvent.click(deleteButton);

      await waitForElementToBeRemoved(
        within(listenToDelete!).queryByRole("menuitem", {
          name: "Delete Listen",
        })
      );

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "fnord",
        "973e5620-829d-46dd-89a8-760d87076287",
        1586523524
      );
      expect(await screen.findAllByTestId("listen")).toHaveLength(25);
    });

    it("does not render delete button if user is not logged in", async () => {
      await act(async () => {
        renderWithProviders(<Listens {...props} />, {
          currentUser: undefined,
        });
      });

      const deleteButton = screen.queryAllByRole("menuitem", {
        name: "Delete Listen",
      });
      expect(deleteButton).toHaveLength(0);
    });

    it("does nothing if the user has no auth token", async () => {
      const spy = jest
        .spyOn(APIService, "deleteListen")
        .mockImplementation(() => Promise.resolve(200));

      await act(async () => {
        renderWithProviders(<Listens {...props} />, {
          APIService,
          currentUser: { auth_token: undefined, name: "iliekcomputers" },
        });
      });

      const listensContainer = await screen.findByTestId("listens");
      const listenCards = await within(listensContainer).findAllByTestId(
        "listen"
      );
      expect(listenCards).toHaveLength(25);
      const listenToDelete = listenCards[0];

      const deleteButton = within(listenToDelete).getByRole("menuitem", {
        name: "Delete Listen",
      });
      await userEvent.click(deleteButton);

      expect(listenCards).toHaveLength(25);

      expect(spy).not.toHaveBeenCalled();
    });

    it("doesn't call removeListenFromListenList or update state if status code is not 200", async () => {
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(500));

      await act(async () => {
        renderWithProviders(<Listens {...props} />, {
          APIService,
          currentUser,
        });
      });

      const listensContainer = await screen.findByTestId("listens");
      const listenCards = await within(listensContainer).findAllByTestId(
        "listen"
      );
      expect(listenCards).toHaveLength(25);
      const listenToDelete = listenCards[0];

      const deleteButton = within(listenToDelete).getByRole("menuitem", {
        name: "Delete Listen",
      });
      await userEvent.click(deleteButton);

      expect(listenCards).toHaveLength(25);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "fnord",
        "973e5620-829d-46dd-89a8-760d87076287",
        1586523524
      );

      await waitFor(
        () => {
          expect(listenCards).toHaveLength(25);
        },
        { timeout: 1000 }
      );
    });

    it("handles error for delete listen", async () => {
      const spy = jest
        .spyOn(APIService, "deleteListen")
        .mockImplementation(() => {
          throw new Error("My error message");
        });

      await act(async () => {
        renderWithProviders(<Listens {...props} />, {
          APIService,
          currentUser,
        });
      });
      const listensContainer = await screen.findByTestId("listens");
      const listenCards = await within(listensContainer).findAllByTestId(
        "listen"
      );
      expect(listenCards).toHaveLength(25);
      const listenToDelete = listenCards[0];
      const deleteButton = within(listenToDelete).getByRole("menuitem", {
        name: "Delete Listen",
      });
      await userEvent.click(deleteButton);
      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "fnord",
        "973e5620-829d-46dd-89a8-760d87076287",
        1586523524
      );
      expect(
        screen.getByText("Error while deleting listen")
      ).toBeInTheDocument();
      expect(screen.getByText("My error message")).toBeInTheDocument();

      await waitFor(
        () => {
          expect(listenCards).toHaveLength(25);
        },
        { timeout: 1000 }
      );
    });
  });

  describe("Pagination", () => {
    const pushStateSpy = jest.spyOn(window.history, "pushState");
    const getListensForUserSpy = jest
      .spyOn(APIService, "getListensForUser")
      .mockImplementation(() => Promise.resolve([]));

    const mockListen: Listen = {
      track_metadata: {
        artist_name: "FNORD",
        track_name: "Have you seen the FNORDs?",
        additional_info: {
          recording_msid: "a6a089da-475b-45cb-a5a8-087caa1a121a",
        },
      },
      listened_at: 1586440100,
      user_name: "mr_monkey",
    };
    afterEach(() => {
      jest.clearAllMocks();
    });

    describe("handleClickOlder", () => {
      it("does nothing if there is no older listens timestamp", async () => {
        await act(async () => {
          renderWithProviders(
            <Listens
              {...props}
              oldestListenTs={listens[listens.length - 1].listened_at}
            />,
            { APIService }
          );
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        expect(olderButton).toHaveAttribute("aria-disabled", "true");
        expect(olderButton).not.toHaveAttribute("href");
        await userEventSession.click(olderButton);

        expect(getListensForUserSpy).not.toHaveBeenCalled();
      });

      it("calls the API to get older listens", async () => {
        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "You mom",
              track_name: "A unique track name",
              release_name: "You mom's best of",
            },
            listened_at: 1586450001,
          },
        ];
        getListensForUserSpy.mockImplementation(() =>
          Promise.resolve(expectedListensArray)
        );

        await act(async () => {
          renderWithProviders(<Listens {...props} />, { APIService });
        });
        const expectedNextListenTimestamp =
          listens[listens.length - 1].listened_at;

        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        await userEventSession.click(olderButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          undefined,
          expectedNextListenTimestamp
        );
        await screen.findByText("A unique track name");
      });

      it("prevents further navigation if it receives not enough listens from API", async () => {
        getListensForUserSpy.mockImplementationOnce(() =>
          Promise.resolve([mockListen])
        );
        await act(async () => {
          renderWithProviders(<Listens {...props} />, { APIService });
        });

        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        expect(olderButton).toHaveAttribute("aria-disabled", "false");
        await userEventSession.click(olderButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          undefined,
          1586440536
        );

        expect(olderButton).toHaveAttribute("aria-disabled", "true");
        expect(olderButton).not.toHaveAttribute("href");
      });

      it("updates the browser history", async () => {
        getListensForUserSpy.mockImplementationOnce(
          (username, minTs, maxTs) => {
            return Promise.resolve([...listens, mockListen]);
          }
        );

        await act(async () => {
          renderWithProviders(<Listens {...props} />, { APIService });
        });

        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        expect(olderButton).toHaveAttribute("aria-disabled", "false");

        await userEventSession.click(olderButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          undefined,
          1586440536
        );
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          "?max_ts=1586440536"
        );

        expect(olderButton).toHaveAttribute("href", "?max_ts=1586440100");
        expect(olderButton).toHaveAttribute("aria-disabled", "false");
      });
    });

    describe("handleClickNewer", () => {
      it("does nothing if there is no newer listens timestamp", async () => {
        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={listens[0].listened_at} />,
            { APIService }
          );
        });

        // button should be disabled if last previousListenTs >= earliest timestamp
        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );
        expect(newerButton).toHaveAttribute("aria-disabled", "true");
        expect(newerButton).not.toHaveAttribute("href");
        await userEventSession.click(newerButton);

        expect(getListensForUserSpy).not.toHaveBeenCalled();
      });

      it("calls the API to get newer listens", async () => {
        const expectedListensArray = [
          {
            track_metadata: {
              artist_name: "You mom",
              track_name: "Another unique track name",
              release_name: "You mom's best of",
            },
            listened_at: Date.now(),
          },
        ];
        getListensForUserSpy.mockImplementation(() =>
          Promise.resolve(expectedListensArray)
        );

        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={Date.now()} />,
            { APIService }
          );
        });
        const expectedPreviousListenTimestamp = listens[0].listened_at;

        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );
        await userEventSession.click(newerButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          expectedPreviousListenTimestamp,
          undefined
        );
        await screen.findByText("Another unique track name");
      });

      it("prevents further navigation if it receives not enough listens from API", async () => {
        getListensForUserSpy.mockImplementationOnce(() =>
          Promise.resolve([mockListen])
        );
        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={Date.now()} />,
            { APIService }
          );
        });

        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );
        expect(newerButton).toHaveAttribute("aria-disabled", "false");
        await userEventSession.click(newerButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          listens[0].listened_at,
          undefined
        );

        expect(newerButton).toHaveAttribute("aria-disabled", "true");
        expect(newerButton).not.toHaveAttribute("href");
      });

      it("updates the browser history", async () => {
        const mostRecentListenTs = listens[0].listened_at;
        const timestamp = Date.now();
        getListensForUserSpy.mockImplementationOnce(
          (username, minTs, maxTs) => {
            return Promise.resolve([
              { ...mockListen, listened_at: timestamp },
              ...listens,
            ]);
          }
        );

        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={timestamp + 100} />,
            { APIService }
          );
        });

        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );
        expect(newerButton).toHaveAttribute("aria-disabled", "false");
        expect(newerButton).toHaveAttribute(
          "href",
          `?min_ts=${mostRecentListenTs}`
        );

        await userEventSession.click(newerButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          mostRecentListenTs,
          undefined
        );
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          `?min_ts=${mostRecentListenTs}`
        );

        expect(newerButton).toHaveAttribute("href", `?min_ts=${timestamp}`);
        expect(newerButton).toHaveAttribute("aria-disabled", "false");
      });
    });

    describe("handleClickOldest", () => {
      it("does nothing if there is no older listens timestamp", async () => {
        await act(async () => {
          renderWithProviders(
            <Listens
              {...props}
              oldestListenTs={listens[listens.length - 1].listened_at}
            />,
            { APIService }
          );
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const oldestButton = await screen.findByLabelText(
          "Navigate to oldest listens"
        );
        expect(oldestButton).toHaveAttribute("aria-disabled", "true");
        expect(oldestButton).not.toHaveAttribute("href");
        await userEventSession.click(oldestButton);

        expect(getListensForUserSpy).not.toHaveBeenCalled();
      });

      it("updates the browser history and disables navigation to oldest", async () => {
        getListensForUserSpy.mockImplementationOnce(
          (username, minTs, maxTs) => {
            return Promise.resolve([
              ...listens,
              {
                ...mockListen,
                listened_at: oldestListenTs,
              },
            ]);
          }
        );

        await act(async () => {
          renderWithProviders(<Listens {...props} />, { APIService });
        });

        const oldestButton = await screen.findByLabelText(
          "Navigate to oldest listens"
        );
        expect(oldestButton).toHaveAttribute("aria-disabled", "false");

        await userEventSession.click(oldestButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(
          user.name,
          oldestListenTs - 1
        );
        expect(pushStateSpy).toHaveBeenCalledWith(
          null,
          "",
          `?min_ts=${oldestListenTs - 1}`
        );

        expect(oldestButton).not.toHaveAttribute("href");
        expect(oldestButton).toHaveAttribute("aria-disabled", "true");
      });
    });
    describe("handleClickNewest", () => {
      it("does nothing if there is no more recent listens timestamp", async () => {
        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={listens[0].listened_at} />,
            { APIService }
          );
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const newestButton = await screen.findByLabelText(
          "Navigate to most recent listens"
        );
        expect(newestButton).toHaveAttribute("aria-disabled", "true");
        expect(newestButton).toHaveAttribute("href", "/");
        await userEventSession.click(newestButton);

        expect(getListensForUserSpy).not.toHaveBeenCalled();
      });

      it("updates the browser history and disables navigation to newest listens", async () => {
        const timestamp = Math.round(Date.now() / 1000);
        await act(async () => {
          renderWithProviders(
            <Listens {...props} latestListenTs={timestamp} />,
            { APIService }
          );
        });

        getListensForUserSpy.mockResolvedValueOnce([
          { ...mockListen, listened_at: timestamp },
          ...listens,
        ]);

        const newestButton = await screen.findByLabelText(
          "Navigate to most recent listens"
        );

        expect(newestButton).toHaveAttribute("href", "/");
        expect(newestButton).toHaveAttribute("aria-disabled", "false");

        await userEventSession.click(newestButton);

        expect(getListensForUserSpy).toHaveBeenCalledWith(user.name);

        expect(pushStateSpy).toHaveBeenCalledWith(null, "", "");

        expect(newestButton).toHaveAttribute("href", "/");
        expect(newestButton).toHaveAttribute("aria-disabled", "true");
      });
    });
  });
});
