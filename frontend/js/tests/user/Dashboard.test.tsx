import * as React from "react";

import {
  screen,
  within,
  act,
  waitFor,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import WS from "jest-websocket-mock";
import { SocketIO as mockSocketIO } from "mock-socket";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import * as recentListensProps from "../__mocks__/recentListensProps.json";
import Listens, { ListensProps } from "../../src/user/Dashboard";
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

const userClickEvent = userEvent.setup();

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
  already_reported_user: false,
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const queryKey = ["dashboard", {}, {}];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const currentUser = { id: 1, name: "iliekcomputers", auth_token: "fnord" };

let mockSearchParam = {};
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: () => {
    const [params, setParams] = React.useState(
      new URLSearchParams(mockSearchParam)
    );
    return [
      params,
      (newParams: typeof mockSearchParam) => {
        mockSearchParam = newParams;
        setParams(new URLSearchParams(newParams));
      },
    ];
  },
}));

describe("Dashboard page", () => {
  jest.setTimeout(10000);
  let server: SetupServerApi;
  beforeAll(async () => {
    const handlers = [
      http.post("/", async (path) => HttpResponse.json(props)),
      http.get("/1/user/*/following", async (path) =>
        HttpResponse.json({ following: [] })
      ),
      http.get("/1/user/*/followers", async (path) =>
        HttpResponse.json({ followers: [] })
      ),
      http.get("/1/user/*/similar-users", async (path) => {
        HttpResponse.json({ payload: [] });
      }),
      http.get("/1/user/*/listen-count", async (path) =>
        HttpResponse.json({ payload: { count: 42 } })
      ),
      http.post("/1/delete-listen", async (path) => HttpResponse.json({})),
      http.get("/1/user/*/similar-to/*", async (path) =>
        HttpResponse.json({ payload: [] })
      ),
      http.get("/1/stats/user/*/artists", async (path) =>
        HttpResponse.json({ payload: [] })
      ),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  afterEach(async () => {
    await queryClient.cancelQueries();
    queryClient.clear();
  });
  afterAll(() => {
    server.close();
  });

  it("renders correctly on the profile page", async () => {
    renderWithProviders(
      <Listens />,
      {
        currentUser,
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });

    expect(screen.getAllByTestId("listen")).toHaveLength(26);
  });

  it("shows the user's listen count component", async () => {
    renderWithProviders(
      <Listens />,
      {
        currentUser,
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });
    
    // Ensure we show a listen count card component, but don't test the contents
    // Tests for it are in ListenCountCard.test.tsx
    screen.getByTestId("listen-count-card");
  });

  it("calls API and removeListenFromListenList correctly, and updates the state", async () => {
    renderWithProviders(
      <Listens />,
      {
        currentUser,
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
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

    expect(await screen.findAllByTestId("listen")).toHaveLength(25);
  });

  it("does not render delete button if user is not logged in", async () => {
    renderWithProviders(
      <Listens />,
      {
        currentUser: {
          name: "foobar",
        },
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
    });

    const deleteButton = screen.queryAllByRole("menuitem", {
      name: "Delete Listen",
    });
    expect(deleteButton).toHaveLength(0);
  });

  it("does nothing if the user has no auth token", async () => {
    renderWithProviders(
      <Listens />,
      {
        currentUser: {
          name: "iliekcomputers",
          auth_token: undefined,
        },
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
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
  });

  it("doesn't call removeListenFromListenList or update state if status code is not 200", async () => {
    server.use(
      http.post("/1/delete-listen", async (path) => {
        return HttpResponse.json({}, { status: 500 });
      })
    );
    renderWithProviders(
      <Listens />,
      {
        currentUser,
      },
      {
        wrapper: reactQueryWrapper,
      }
    );

    await waitFor(() => {
      // Wait for data to be successfully loaded
      const state = queryClient.getQueryState(queryKey);
      expect(state?.status === "success").toBeTruthy();
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

      renderWithProviders(
        <Listens />,
        {
          currentUser,
        },
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        // Wait for data to be successfully loaded
        const state = queryClient.getQueryState(queryKey);
        expect(state?.status === "success").toBeTruthy();
      });

      await websocketServer.connected;
      await returnPromise; // See at the beginning of this test

      const websocketClients = websocketServer.server.clients();
      expect(websocketClients.length).toBeGreaterThanOrEqual(1);
      expect(receivedUserNameMessage).toBeTruthy();
    });

    it('calls correct handler for "listen" event', async () => {
      renderWithProviders(
        <Listens />,
        {
          currentUser,
        },
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        // Wait for data to be successfully loaded
        const state = queryClient.getQueryState(queryKey);
        expect(state?.status === "success").toBeTruthy();
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
      renderWithProviders(
        <Listens />,
        {
          currentUser,
        },
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        // Wait for data to be successfully loaded
        const state = queryClient.getQueryState(queryKey);
        expect(state?.status === "success").toBeTruthy();
      });

      await websocketServer.connected;
      expect(screen.queryAllByTestId("listen")).toHaveLength(26);

      const playingNowListen: Listen = {
        ...mockListen,
        listened_at: Date.now(),
        playing_now: true,
      };

      await waitFor(() => {
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
      renderWithProviders(
        <Listens />,
        {
          currentUser,
        },
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        // Wait for data to be successfully loaded
        const state = queryClient.getQueryState(queryKey);
        expect(state?.status === "success").toBeTruthy();
      });

      await websocketServer.connected;

      // Add 7 new listens
      await waitFor(async () => {
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

  describe("Pagination", () => {
    afterEach(() => {
      jest.clearAllMocks();
    });

    describe("handleClickOlder", () => {
      it("older button should be disabled if there is no older listens timestamp", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              oldestListenTs: listens[listens.length - 1].listened_at,
            });
          })
        );

        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        expect(olderButton).toHaveAttribute("aria-disabled", "true");
        await userClickEvent.click(olderButton);
      });

      it("older button should have a link to older listen page", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              oldestListenTs: Math.round(
                new Date("2019-04-09T10:12:04Z").getTime() / 1000
              ),
            });
          })
        );
        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          },
          true
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        const olderButton = await screen.findByLabelText(
          "Navigate to older listens"
        );
        expect(olderButton).toHaveAttribute("aria-disabled", "false");
        expect(olderButton).toHaveAttribute("href", "/?max_ts=1586440536");
      });
    });

    describe("handleClickNewer", () => {
      it("newer button should be disabled if there is no newer listens timestamp", async () => {
        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        // button should be disabled if last previousListenTs >= earliest timestamp
        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );
        expect(newerButton).toHaveAttribute("aria-disabled", "true");
      });

      it("newer button should have a link to newer listen page", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              latestListenTs: new Date("2021-09-14T03:16:16.161Z").getTime(),
            });
          })
        );
        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        const newerButton = await screen.findByLabelText(
          "Navigate to more recent listens"
        );

        expect(newerButton).toHaveAttribute("aria-disabled", "false");
        expect(newerButton).toHaveAttribute("href", "/?min_ts=1586523524");
      });
    });

    describe("handleClickOldest", () => {
      it("does nothing if there is no older listens timestamp", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              oldestListenTs: listens[listens.length - 1].listened_at,
            });
          })
        );

        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const oldestButton = await screen.findByLabelText(
          "Navigate to oldest listens"
        );
        expect(oldestButton).toHaveAttribute("aria-disabled", "true");
      });

      it("oldest button should have a link to oldest listen page", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              oldestListenTs: Math.round(
                new Date("2019-04-09T10:12:04Z").getTime() / 1000
              ),
            });
          })
        );
        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        const oldestButton = await screen.findByLabelText(
          "Navigate to oldest listens"
        );
        expect(oldestButton).toHaveAttribute("aria-disabled", "false");
        expect(oldestButton).toHaveAttribute("href", "/?min_ts=1554804723");
      });
    });
    describe("handleClickNewest", () => {
      it("newest button is disabled if there is no more recent listens timestamp", async () => {
        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              latestListenTs: listens[0].listened_at,
            });
          })
        );

        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        // button should be disabled if last listen's listened_at <= oldestListenTs
        const newestButton = await screen.findByLabelText(
          "Navigate to most recent listens"
        );
        expect(newestButton).toHaveAttribute("aria-disabled", "true");
      });

      it("newest button should have a link to newest listen page", async () => {
        const timestamp = Math.round(
          new Date("2024-09-14T03:16:16.161Z").getTime() / 1000
        );

        server.use(
          http.post("/", async (path) => {
            return HttpResponse.json({
              ...props,
              latestListenTs: timestamp,
            });
          })
        );

        renderWithProviders(
          <Listens />,
          {
            currentUser,
          },
          {
            wrapper: reactQueryWrapper,
          }
        );

        await waitFor(() => {
          // Wait for data to be successfully loaded
          const state = queryClient.getQueryState(queryKey);
          expect(state?.status === "success").toBeTruthy();
        });

        const newestButton = await screen.findByLabelText(
          "Navigate to most recent listens"
        );

        expect(newestButton).toHaveAttribute("href", "/");
        expect(newestButton).toHaveAttribute("aria-disabled", "false");
      });
    });
  });
});
