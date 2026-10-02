import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WatchButton from "../../src/event/WatchButton";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

const eventMBID = "e7dc43dd-1360-45fe-8858-2fe26006fca9";

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {
    id: 2,
    name: "iliekcomputers",
    auth_token: "FNORD",
  },
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

const renderWatchButton = (
  props: Partial<React.ComponentProps<typeof WatchButton>> = {}
) =>
  render(
    <GlobalAppContext.Provider value={globalContext}>
      <WatchButton
        eventMBID={eventMBID}
        loggedInUserWatchesEvent={false}
        {...props}
      />
    </GlobalAppContext.Provider>
  );

describe("<WatchButton />", () => {
  beforeEach(() => {
    jest.restoreAllMocks();
  });

  it("says whether the event is watched, and offers to unwatch it on hover", async () => {
    renderWatchButton({ loggedInUserWatchesEvent: true });
    const watchButton = screen.getByRole("button", { name: "Watching" });
    expect(watchButton).toHaveClass("lb-watch-button", "btn-info");

    await userEvent.hover(watchButton);
    expect(watchButton).toHaveTextContent("Unwatch");
  });

  it("watches the event", async () => {
    const updateWatchedEvents = jest.fn();
    const watchSpy = jest
      .spyOn(globalContext.APIService, "watchEvent")
      .mockResolvedValue({ status: 200 });
    renderWatchButton({ updateWatchedEvents });

    await userEvent.click(screen.getByRole("button", { name: "Watch" }));

    await waitFor(() => {
      expect(watchSpy).toHaveBeenCalledWith(eventMBID, "FNORD");
    });
    expect(updateWatchedEvents).toHaveBeenCalledWith(eventMBID, "watch");
    // the theme gives outline buttons a border that filled ones don't have, so switching would resize it
    expect(screen.getByRole("button", { name: "Watching" })).toHaveClass(
      "btn-info"
    );
  });

  it("stops watching the event", async () => {
    const updateWatchedEvents = jest.fn();
    const unwatchSpy = jest
      .spyOn(globalContext.APIService, "unwatchEvent")
      .mockResolvedValue({ status: 200 });
    renderWatchButton({ loggedInUserWatchesEvent: true, updateWatchedEvents });

    await userEvent.hover(screen.getByRole("button", { name: "Watching" }));
    await userEvent.click(screen.getByRole("button", { name: "Unwatch" }));

    await waitFor(() => {
      expect(unwatchSpy).toHaveBeenCalledWith(eventMBID, "FNORD");
    });
    expect(updateWatchedEvents).toHaveBeenCalledWith(eventMBID, "unwatch");
    expect(screen.getByRole("button", { name: "Watch" })).toBeInTheDocument();
  });

  it("shows an error if watching the event fails", async () => {
    const updateWatchedEvents = jest.fn();
    jest
      .spyOn(globalContext.APIService, "watchEvent")
      .mockResolvedValue({ status: 400 });
    renderWatchButton({ updateWatchedEvents });

    await userEvent.click(screen.getByRole("button", { name: "Watch" }));

    expect(
      await screen.findByRole("button", { name: "Error!!" })
    ).toBeInTheDocument();
    expect(updateWatchedEvents).not.toHaveBeenCalled();
  });

  it("follows changes to whether the event is watched", async () => {
    const { rerender } = renderWatchButton();
    expect(screen.getByRole("button", { name: "Watch" })).toBeInTheDocument();

    rerender(
      <GlobalAppContext.Provider value={globalContext}>
        <WatchButton eventMBID={eventMBID} loggedInUserWatchesEvent />
      </GlobalAppContext.Provider>
    );

    expect(
      await screen.findByRole("button", { name: "Watching" })
    ).toBeInTheDocument();
  });
});
