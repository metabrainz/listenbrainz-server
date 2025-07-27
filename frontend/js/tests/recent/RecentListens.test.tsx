import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import fetchMock from "jest-fetch-mock";
import { BrowserRouter } from "react-router";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIServiceClass from "../../src/utils/APIService";

import * as recentListensProps from "../__mocks__/recentListensProps.json";
import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";

import {
  RecentListensWrapper,
  RecentListensProps,
} from "../../src/recent/RecentListens"; // Import the wrapper component
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../test-react-query";

const {
  listens,
  spotify,
  youtube,
  globalListenCount,
  globalUserCount,
} = recentListensProps;

const pinnedRecordingFromAPI: PinnedRecording = {
  created: 1605927742,
  pinned_until: 1605927893,
  blurb_content:
    "Our perception of the passing of time is really just a side-effect of gravity",
  recording_mbid: "recording_mbid",
  row_id: 1,
  track_metadata: {
    artist_name: "TWICE",
    track_name: "Feel Special",
    additional_info: {
      release_mbid: "release_mbid",
      recording_msid: "recording_msid",
      recording_mbid: "recording_mbid",
    },
  },
};

const loaderDataProps: RecentListensProps = {
  listens,
  globalListenCount,
  globalUserCount,
  recentDonors: [
    {
      id: 123456,
      donated_at: "",
      donation: 42,
      currency: "eur",
      musicbrainz_id: "Foo",
      is_listenbrainz_user: true,
      listenCount: 1234,
      playlistCount: 123,
      pinnedRecording: pinnedRecordingFromAPI,
    },
    {
      id: 1234,
      donated_at: "",
      donation: 123,
      currency: "eur",
      musicbrainz_id: "Bar",
      is_listenbrainz_user: true,
      listenCount: 999,
      playlistCount: 0,
      pinnedRecording: pinnedRecordingFromAPI,
    },
  ],
};

const globalContext: GlobalAppContextT = {
  APIService: new APIServiceClass("foo"),
  websocketsUrl: "",
  youtubeAuth: youtube as YoutubeUser,
  spotifyAuth: spotify as SpotifyUser,
  currentUser: { id: 1, name: "iliekcomputers", auth_token: "fnord" },
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIServiceClass("foo"),
    { name: "Fnord" }
  ),
};

// Mock `useLoaderData` from `react-router`
const mockUseLoaderData = jest.fn().mockReturnValue(loaderDataProps);
jest.mock("react-router", () => ({
  ...jest.requireActual("react-router"),
  useLoaderData: () => mockUseLoaderData(),
}));

// We need to mock useBrainzPlayerDispatch to check if it's called
const mockDispatch = jest.fn();
jest.mock("../../src/common/brainzplayer/BrainzPlayerContext", () => ({
  useBrainzPlayerDispatch: () => mockDispatch,
}));

describe("RecentListensWrapper", () => {
  beforeAll(() => {
    fetchMock.enableMocks();
    fetchMock.mockIf(
      (input) => input.url.endsWith("/listen-count"),
      () => {
        return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
      }
    );
    fetchMock.mockIf(
      (input) => input.url.startsWith("https://api.spotify.com"),
      () => {
        return Promise.resolve(JSON.stringify({}));
      }
    );
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page correctly with listens", async () => {
    render(
      <GlobalAppContext.Provider value={globalContext}>
        <BrowserRouter>
          <ReactQueryWrapper>
            <RecentListensWrapper />
          </ReactQueryWrapper>
        </BrowserRouter>
      </GlobalAppContext.Provider>
    );

    expect(
      screen.getByRole("heading", { name: /Global listens/i })
    ).toBeInTheDocument();

    // Check for the global listen count and user count
    expect(screen.getByText("666")).toBeInTheDocument();
    expect(screen.getByText("songs played")).toBeInTheDocument();
    // Check for the global user count
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("users")).toBeInTheDocument();

    // Check if ListenCards are rendered
    expect(screen.getAllByTestId("listen")).toHaveLength(25);
    expect(screen.getByText("Falling")).toBeInTheDocument();

    // Check for the presence of the RecentDonorsCard and FlairsExplanationButton
    expect(screen.getByText(/Recent Donors/i)).toBeInTheDocument();
    expect(screen.getByText("Foo")).toBeInTheDocument();
    expect(screen.getByText("42€")).toBeInTheDocument();
    expect(screen.getByText("Bar")).toBeInTheDocument();
    expect(screen.getByText("123€")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /why are some names a n i m a t e d \?/i,
      })
    ).toBeInTheDocument();
  });

  it("renders 'No listens to show' when listens list is empty", async () => {
    mockUseLoaderData.mockReturnValueOnce({ ...loaderDataProps, listens: [] });

    render(
      <GlobalAppContext.Provider value={globalContext}>
        <BrowserRouter>
          <ReactQueryWrapper>
            <RecentListensWrapper />
          </ReactQueryWrapper>
        </BrowserRouter>
      </GlobalAppContext.Provider>
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /No listens to show/i })
      ).toBeInTheDocument();
    });
    // Ensure no ListenCards are rendered
    expect(screen.queryByTestId("listen")).not.toBeInTheDocument();
  });

  it("sets ambient queue when listens data changes", async () => {
    mockUseLoaderData.mockReturnValueOnce({
      ...loaderDataProps,
      listens: recentListensPropsOneListen.listens,
    });

    const { rerender } = render(
      <GlobalAppContext.Provider value={globalContext}>
        <BrowserRouter>
          <ReactQueryWrapper>
            <RecentListensWrapper />
          </ReactQueryWrapper>
        </BrowserRouter>
      </GlobalAppContext.Provider>
    );

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalledWith({
        type: "SET_AMBIENT_QUEUE",
        data: recentListensPropsOneListen.listens,
      });
    });

    mockUseLoaderData.mockReturnValueOnce({
      ...loaderDataProps,
      // a different listen object
      listens: [{ name: "New Listen" }],
    });

    // Simulate an update to listens prop to trigger useEffect again
    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <BrowserRouter>
          <ReactQueryWrapper>
            <RecentListensWrapper />
          </ReactQueryWrapper>
        </BrowserRouter>
      </GlobalAppContext.Provider>
    );

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalledWith({
        type: "SET_AMBIENT_QUEUE",
        data: [{ name: "New Listen" }],
      });
      // Called once initially, once on update
      expect(mockDispatch).toHaveBeenCalledTimes(2);
    });
  });
});
