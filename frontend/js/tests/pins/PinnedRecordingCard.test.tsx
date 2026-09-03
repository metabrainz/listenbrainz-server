import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import PinnedRecordingCard, {
  PinnedRecordingCardProps,
} from "../../src/user/components/PinnedRecordingCard";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../test-react-query";

const user = {
  id: 1,
  name: "name",
  auth_token: "auth_token",
};

const globalProps: GlobalAppContextT = {
  APIService: new APIServiceClass(""),
  websocketsUrl: "",
  currentUser: user,
  spotifyAuth: {},
  youtubeAuth: {},
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIServiceClass("foo"),
    { name: "Fnord" }
  ),
};

const pinnedRecording: PinnedRecording = {
  blurb_content: "I LOVE",
  created: 1111111111,
  // In the future, so not expired
  pinned_until: 9999999999,
  row_id: 1,
  recording_mbid: "98255a8c-017a-4bc7-8dd6-1fa36124572b",
  track_metadata: {
    artist_name: "Rick Astley",
    track_name: "Never Gonna Give You Up",
  },
};

const expiredPinnedRecording: PinnedRecording = {
  ...pinnedRecording,
  // In the past, so expired
  pinned_until: 1111122222,
};

const props: PinnedRecordingCardProps = {
  pinnedRecording,
  isCurrentUser: true,
  removePinFromPinsList: jest.fn(),
};

describe("PinnedRecordingCard", () => {
  // Helper to render and get a ref to the component instance
  const setupComponent = (
    propsOverride?: Partial<PinnedRecordingCardProps>,
    globalPropsOverride?: Partial<GlobalAppContextT>
  ) => {
    let pinnedRecordingCardInstance: PinnedRecordingCard | null;
    render(
      <GlobalAppContext.Provider
        value={{ ...globalProps, ...globalPropsOverride }}
      >
        <ReactQueryWrapper>
          <PinnedRecordingCard
            {...props}
            {...propsOverride}
            ref={(ref) => {
              pinnedRecordingCardInstance = ref;
            }}
          />
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    // Wait for the ref to be available
    return waitFor(() =>
      expect(pinnedRecordingCardInstance).not.toBeNull()
    ).then(() => pinnedRecordingCardInstance!);
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders correctly", () => {
    setupComponent();

    // Check for the presence of the main component class
    const cardElement = screen
      .getByText(/I LOVE/)
      .closest(".pinned-recording-card");
    expect(cardElement).toBeInTheDocument();
    expect(
      screen.getByText(pinnedRecording.track_metadata.track_name)
    ).toBeInTheDocument();
    expect(
      screen.getByText(pinnedRecording.track_metadata.artist_name)
    ).toBeInTheDocument();
  });

  describe("determineIfCurrentlyPinned", () => {
    it("renders as currently pinned when pinned_until > now", () => {
      setupComponent();
      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      expect(cardElement).toHaveClass("currently-pinned");
    });

    it("renders as not currently pinned when pinned_until < now", () => {
      setupComponent({ pinnedRecording: expiredPinnedRecording });
      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      expect(cardElement).not.toHaveClass("currently-pinned");
    });
  });

  describe("unpinRecording", () => {
    let unpinRecordingSpy = jest
      .spyOn(globalProps.APIService, "unpinRecording")
      .mockImplementation(() => Promise.resolve(200));

    it("calls API and updates currentlyPinned class in DOM", async () => {
      const instance = await setupComponent();

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Initially pinned
      expect(cardElement).toHaveClass("currently-pinned");

      await instance.unpinRecording();

      await waitFor(() => {
        expect(unpinRecordingSpy).toHaveBeenCalledTimes(1);
        expect(unpinRecordingSpy).toHaveBeenCalledWith(
          globalProps.currentUser?.auth_token
        );
      });

      // Verify DOM update reflects state change
      expect(cardElement).not.toHaveClass("currently-pinned");
    });

    it("does nothing if isCurrentUser is false", async () => {
      const instance = await setupComponent({ isCurrentUser: false });

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain pinned
      expect(cardElement).toHaveClass("currently-pinned");

      await instance.unpinRecording();

      expect(unpinRecordingSpy).toHaveBeenCalledTimes(0);
      expect(cardElement).toHaveClass("currently-pinned");
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const instance = await setupComponent(undefined, {
        currentUser: { auth_token: undefined, name: "test" },
      });

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain pinned
      expect(cardElement).toHaveClass("currently-pinned");

      await instance.unpinRecording();

      expect(unpinRecordingSpy).toHaveBeenCalledTimes(0);
      expect(cardElement).toHaveClass("currently-pinned");
    });

    it("doesn't update currentlyPinned if status code is not 200", async () => {
      const instance = await setupComponent();

      // Non-200 status
      unpinRecordingSpy.mockImplementation(() => Promise.resolve(201));

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain pinned
      expect(cardElement).toHaveClass("currently-pinned");

      await instance.unpinRecording();

      await waitFor(() => {
        // API call should still happen
        expect(unpinRecordingSpy).toHaveBeenCalled();
      });
      // State should not change
      expect(cardElement).toHaveClass("currently-pinned");
    });

    it("calls handleError if error is returned", async () => {
      const instance = await setupComponent();
      const instanceHandleErrorSpy = jest.spyOn(instance, "handleError");

      const error = new Error("error");
      unpinRecordingSpy.mockImplementation(() => {
        throw error;
      });

      await instance.unpinRecording();

      await waitFor(() => {
        expect(instanceHandleErrorSpy).toHaveBeenCalledTimes(1);
        expect(instanceHandleErrorSpy).toHaveBeenCalledWith(
          error,
          "Error while unpinning track"
        );
      });
    });
  });

  describe("deletePin", () => {
    let deletePinSpy = jest
      .spyOn(globalProps.APIService, "deletePin")
      .mockImplementation(() => Promise.resolve(200));

    beforeEach(() => {
      jest.clearAllMocks();
    });

    it("calls API and updates isDeleted and currentlyPinned classes in DOM", async () => {
      // Use fake timers for setTimeout tests
      jest.useFakeTimers();

      const instance = await setupComponent();

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Initially not deleted
      expect(cardElement).not.toHaveClass("deleted");
      // Initially pinned
      expect(cardElement).toHaveClass("currently-pinned");

      await instance.deletePin(pinnedRecording);

      await waitFor(() => {
        expect(deletePinSpy).toHaveBeenCalledTimes(1);
        expect(deletePinSpy).toHaveBeenCalledWith(
          globalProps.currentUser?.auth_token,
          pinnedRecording.row_id
        );
      });

      await waitFor(() => {
        // Verify DOM updates
        expect(cardElement).toHaveClass("deleted");
        expect(cardElement).not.toHaveClass("currently-pinned");
      });

      // Advance timers for setTimeout related to removePinFromPinsList
      jest.advanceTimersByTime(1000);

      await waitFor(() => {
        expect(props.removePinFromPinsList).toHaveBeenCalledTimes(1);
        expect(props.removePinFromPinsList).toHaveBeenCalledWith(
          props.pinnedRecording
        );
      });

      // Restore real timers
      jest.useRealTimers();
    });

    it("does nothing if isCurrentUser is false", async () => {
      const instance = await setupComponent({ isCurrentUser: false });

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain not deleted
      expect(cardElement).not.toHaveClass("deleted");

      await instance.deletePin(pinnedRecording);

      expect(deletePinSpy).toHaveBeenCalledTimes(0);
      expect(cardElement).not.toHaveClass("deleted");
    });

    it("does nothing if currentUser.authtoken is not set", async () => {
      const instance = await setupComponent(undefined, {
        currentUser: undefined,
      });

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain not deleted
      expect(cardElement).not.toHaveClass("deleted");

      await instance.deletePin(pinnedRecording);

      expect(deletePinSpy).toHaveBeenCalledTimes(0);
      expect(cardElement).not.toHaveClass("deleted");
    });

    it("doesn't update state if response status code is not 200", async () => {
      const instance = await setupComponent();

      // Non-200 status
      deletePinSpy.mockImplementationOnce(() => Promise.resolve(201));

      const cardElement = screen
        .getByText(/I LOVE/)
        .closest(".pinned-recording-card");
      // Should remain not deleted
      expect(cardElement).not.toHaveClass("deleted");

      await instance.deletePin(pinnedRecording);

      await waitFor(() => {
        expect(deletePinSpy).toHaveBeenCalled();
      });
      expect(cardElement).not.toHaveClass("deleted");
    });

    it("calls handleError if error is returned", async () => {
      const instance = await setupComponent();
      const instanceHandleErrorSpy = jest.spyOn(instance, "handleError");

      const error = new Error("error");
      deletePinSpy.mockImplementation(() => {
        throw error;
      });

      await instance.deletePin(pinnedRecording);

      await waitFor(() => {
        expect(instanceHandleErrorSpy).toHaveBeenCalledTimes(1);
        expect(instanceHandleErrorSpy).toHaveBeenCalledWith(
          error,
          "Error while deleting pin"
        );
      });
    });
  });
});
