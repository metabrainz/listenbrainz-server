import * as React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router";
import NiceModal from "@ebay/nice-modal-react";
import { set, omit } from "lodash";

import ListenCard, {
  ListenCardProps,
} from "../../../src/common/listens/ListenCard";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIServiceClass from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import * as utils from "../../../src/utils/utils";
import { ReactQueryWrapper } from "../../test-react-query";
import { textContentMatcher } from "../../test-utils/rtl-test-utils";
import { ToastContainer } from "react-toastify";
import fetchMock from "jest-fetch-mock";
import { createBrainzPlayerSettings } from "../../test-utils/BrainzPlayer-test-utils";
jest.unmock("react-toastify");

fetchMock.enableMocks();
const user = userEvent.setup();

const listen: Listen = {
  listened_at: 1672531200, // Jan 1, 2023
  playing_now: false,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
    additional_info: {
      duration_ms: 123000, // 2:03
      release_mbid: "some-release-mbid",
      recording_msid: "some-recording-msid",
      recording_mbid: "some-recording-mbid",
      artist_mbids: ["some-artist-mbid"],
    },
  },
  user_name: "test",
};

const defaultProps: ListenCardProps = {
  listen,
  showTimestamp: true,
  showUsername: true,
};

const defaultContext: GlobalAppContextT = {
  APIService: new APIServiceClass(""),
  websocketsUrl: "",
  currentUser: { auth_token: "test-auth-token", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIServiceClass(""),
    { name: "Fnord" }
  ),
  userPreferences: { brainzplayer: createBrainzPlayerSettings({ brainzplayerEnabled: true }) },
};

// Helper function to render the component with all necessary providers.
const renderComponent = (
  props: Partial<ListenCardProps> = {},
  context: Partial<GlobalAppContextT> = {}
) => {
  return render(
    <BrowserRouter>
      <GlobalAppContext.Provider value={{ ...defaultContext, ...context }}>
        <ReactQueryWrapper>
          <ToastContainer />
          <NiceModal.Provider>
            <ListenCard {...defaultProps} {...props} />
          </NiceModal.Provider>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    </BrowserRouter>
  );
};

describe("ListenCard", () => {
  it("renders correctly", () => {
    renderComponent();
    expect(screen.getByTestId("listen")).toBeInTheDocument();
    expect(screen.getByText("Bird's Lament")).toBeInTheDocument();
    expect(screen.getByText("Moondog")).toBeInTheDocument();
  });

  it("renders correctly for a 'playing_now' listen", () => {
    const playingNowListen = { ...listen, playing_now: true };
    renderComponent({ listen: playingNowListen });
    expect(screen.getByText(/Listening now/)).toBeInTheDocument();
    expect(screen.getByTitle(/Recommend to my followers/)).toBeInTheDocument();
  });

  it("renders timestamp using preciseTimestamp", () => {
    const preciseTimestampSpy = jest.spyOn(utils, "preciseTimestamp");
    renderComponent();
    expect(preciseTimestampSpy).toHaveBeenCalled();
    expect(
      screen.getByText(utils.preciseTimestamp(listen.listened_at * 1000))
    ).toBeInTheDocument();
  });

  it("should use mapped MBIDs if listen does not have user-submitted MBIDs", () => {
    const mappedListen: Listen = {
      listened_at: 0,
      playing_now: false,
      user_name: "test",
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        mbid_mapping: {
          release_mbid: "mapped-release-mbid",
          recording_mbid: "mapped-recording-mbid",
          artist_mbids: ["mapped-artist-mbid"],
          artists: [
            {
              artist_mbid: "mapped-artist-mbid",
              artist_credit_name: "Moondog",
              join_phrase: "",
            },
          ],
        },
      },
    };
    renderComponent({ listen: mappedListen });
    // Check for the link to the artist page using the mapped MBID
    expect(screen.getByRole("link", { name: "Moondog" })).toHaveAttribute(
      "href",
      "/artist/mapped-artist-mbid/"
    );
  });

  it("should render a play button by default", () => {
    renderComponent();
    const playButton = screen.getByRole("button", { name: "Play" });
    expect(playButton).toBeInTheDocument();
    expect(playButton).toHaveClass("play-button");
  });

  it("should render a play button if BrainzPlayer is enabled in preferences", () => {
    renderComponent(
      {},
      { userPreferences: { brainzplayer:createBrainzPlayerSettings( { brainzplayerEnabled: true } )} }
    );
    expect(screen.queryByRole("button", { name: "Play" })).toBeInTheDocument();
  });

  it("should not render play button when BrainzPlayer is disabled in preferences", () => {
    renderComponent(
      {},
      { userPreferences: { brainzplayer:createBrainzPlayerSettings({ brainzplayerEnabled: false }) } }
    );
    expect(
      screen.queryByRole("button", { name: "Play" })
    ).not.toBeInTheDocument();
  });

  it("should send a 'play-listen' event to BrainzPlayer via postMessage when play button is clicked", async () => {
    const postMessageSpy = jest.spyOn(window, "postMessage");
    renderComponent();

    await user.click(screen.getByRole("button", { name: "Play" }));

    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "play-listen", payload: listen },
      window.location.origin
    );
  });

  it("should not send a 'play-listen' event if the listen is already playing", async () => {
    const postMessageSpy = jest.spyOn(window, "postMessage");
    renderComponent();

    // Simulate that this listen is now playing via a window message
    act(() => {
      fireEvent(
        window,
        new MessageEvent("message", {
          data: {
            brainzplayer_event: "current-listen-change",
            payload: listen,
          },
          origin: window.location.origin,
        })
      );
    });

    // The button should now be in a "playing" state, but we click it anyway
    await user.click(screen.getByRole("button", { name: "Play" }));

    // The spy was called once for the initial setup, but not again for the click
    expect(postMessageSpy).not.toHaveBeenCalled();
  });

  it("should render the formatted duration for duration_ms", () => {
    renderComponent();
    expect(screen.getByTitle("Duration")).toHaveTextContent("2:03");
  });
  it("should render the formatted duration for duration (in seconds)", () => {
    // We remove the duration_ms field and replace it with a duration field
    const listenWithDuration = omit(
      listen,
      "track_metadata.additional_info.duration_ms"
    );
    set(listenWithDuration, "track_metadata.additional_info.duration", 142);
    renderComponent({ listen: listenWithDuration });
    expect(screen.getByTitle("Duration")).toHaveTextContent("2:22");
  });
  describe("recommendTrackToFollowers", () => {
    it("should recommend track to followers when 'Recommend' button is clicked", async () => {
      const recommendAPISpy = jest
        .spyOn(defaultContext.APIService, "recommendTrackToFollowers")
        .mockResolvedValue(200);
      renderComponent();

      // Open the dropdown menu
      await user.click(screen.getByRole("button", { name: "More actions" }));

      // Click the recommend button
      const recommendButton = await screen.findByText(
        "Recommend to my followers"
      );
      await user.click(recommendButton);

      expect(recommendAPISpy).toHaveBeenCalledTimes(1);
      expect(recommendAPISpy).toHaveBeenCalledWith("test", "test-auth-token", {
        recording_msid: "some-recording-msid",
        recording_mbid: "some-recording-mbid",
      });
      // Check for success message toast
      await screen.findByText("You recommended a track to your followers");
      await screen.findByText("Bird's Lament by Moondog");
    });
    it("should not recommend track user token not set", async () => {
      const recommendAPISpy = jest
        .spyOn(defaultContext.APIService, "recommendTrackToFollowers")
        .mockResolvedValue(200);
      renderComponent(undefined, { currentUser: { name: "Fnord" } });

      // Open the dropdown menu
      await user.click(screen.getByRole("button", { name: "More actions" }));

      // Click the recommend button
      const recommendButton = await screen.findByText(
        "Recommend to my followers"
      );
      await user.click(recommendButton);

      expect(recommendAPISpy).not.toHaveBeenCalled();
    });
    it("should show an error toast if API call fails", async () => {
      const recommendAPISpy = jest
        .spyOn(defaultContext.APIService, "recommendTrackToFollowers")
        .mockRejectedValue("fake error message");
      renderComponent();

      // Open the dropdown menu
      await user.click(screen.getByRole("button", { name: "More actions" }));

      // Click the recommend button
      const recommendButton = await screen.findByText(
        "Recommend to my followers"
      );
      await user.click(recommendButton);
      await screen.findByText(
        "We encountered an error when trying to recommend the track to your followers"
      );
      await screen.findByText("fake error message");
    });
  });
  describe("pinRecordingModal", () => {
    it("should open PinRecordingModal when 'Pin this track' is clicked", async () => {
      renderComponent();

      await user.click(screen.getByRole("button", { name: "More actions" }));
      await user.click(await screen.findByText("Pin this track"));

      // Check if the modal title is visible
      await screen.findByText("Pin this track to your profile");
      // Check that track title and artist names appear on the modal
      await screen.findByText(textContentMatcher("Bird's Lament by Moondog"));
    });
  });
});
