import * as React from "react";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import * as pinsPageProps from "../__mocks__/userPinsProps.json";
import UserPins, {
  UserPinsProps,
} from "../../src/user/taste/components/UserPins";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../test-react-query";
import {
  render,
  screen,
  waitForElementToBeRemoved,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { textContentMatcher } from "../test-utils/rtl-test-utils";

const user = userEvent.setup();

const defaultContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: pinsPageProps.youtube as YoutubeUser,
  spotifyAuth: pinsPageProps.spotify as SpotifyUser,
  currentUser: { ...pinsPageProps.user, auth_token: "fnord" },
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};
const defaultProps: UserPinsProps = {
  ...pinsPageProps,
};
// Helper function to render the component with all necessary providers.
const renderComponent = (
  props: Partial<UserPinsProps> = {},
  context: Partial<GlobalAppContextT> = {}
) => {
  return render(
    <GlobalAppContext.Provider value={{ ...defaultContext, ...context }}>
      <ReactQueryWrapper>
        <UserPins {...defaultProps} {...props} />
      </ReactQueryWrapper>
    </GlobalAppContext.Provider>
  );
};

const APIPinsPageTwo = {
  count: 1,
  offset: 25,
  pinned_recordings: [
    {
      blurb_content: null,
      created: 1628711647,
      pinned_until: 1628711786,
      recording_mbid: null,
      recording_msid: "a539519f-e99e-4a6a-acc8-b80f6cd38476",
      row_id: 30,
      track_metadata: {
        artist_name: "Elder",
        track_name: "Ne Plus Ultra",
      },
    },
  ],
  total_count: 26,
  user_name: "jdaok",
};

describe("UserPins", () => {
  it("renders correctly", () => {
    renderComponent();
    expect(screen.getByTestId("pinned-recordings")).toBeInTheDocument();
    expect(screen.getByText("All the Way Down")).toBeInTheDocument();
    expect(screen.getByText("Kelela")).toBeInTheDocument();
    expect(screen.getByText(textContentMatcher("Your Pins")));
  });

  it("renders the correct number of pinned recordings", () => {
    renderComponent();
    // PinnedRecordingCards render a ListenCard under the hood which we can target
    const pinnedRecordings = screen.getAllByTestId("listen");
    expect(pinnedRecordings).toHaveLength(defaultProps.pins.length);
  });

  describe("handleLoadMore", () => {
    describe("handleClickOlder", () => {
      it("does nothing if page >= maxPage", async () => {
        const getPinsForUserSpy = jest.spyOn(
          defaultContext.APIService,
          "getPinsForUser"
        );

        renderComponent({ totalCount: 25 });

        await user.click(
          screen.getByRole("button", { name: "No more pins to show" })
        );

        expect(getPinsForUserSpy).not.toHaveBeenCalled();
      });

      it("calls the API to get next page", async () => {
        const getPinsForUserSpy = jest
          .spyOn(defaultContext.APIService, "getPinsForUser")
          .mockResolvedValue(APIPinsPageTwo);

        renderComponent();

        expect(screen.queryByText("Elder")).not.toBeInTheDocument();
        expect(screen.queryByText("Ne Plus Ultra")).not.toBeInTheDocument();
        let pinnedRecordings = screen.getAllByTestId("listen");
        expect(pinnedRecordings).toHaveLength(25);

        // second page is fetchable
        await user.click(screen.getByRole("button", { name: "Load more…" }));

        expect(getPinsForUserSpy).toHaveBeenCalledWith("jdaok", 25, 25);
        // The text in the button also changes
        expect(
          screen.getByRole("button", { name: "No more pins to show" })
        ).toBeDisabled();
        // result should combine previous pins and new pin
        pinnedRecordings = screen.getAllByTestId("listen");
        expect(pinnedRecordings).toHaveLength(26);
        expect(screen.getByText("All the Way Down")).toBeInTheDocument();
        expect(screen.getByText("Kelela")).toBeInTheDocument();
        expect(screen.getByText("Elder")).toBeInTheDocument();
        expect(screen.getByText("Ne Plus Ultra")).toBeInTheDocument();
      });
    });
  });

  describe("removePinFromPinsList", () => {
    it("updates the listens state after removing particular pin", async () => {
      const deletePinSpy = jest
        .spyOn(defaultContext.APIService, "deletePin")
        .mockResolvedValue(200);

      renderComponent();

      const pinnedRecordings = screen.getAllByTestId("listen");
      expect(pinnedRecordings).toHaveLength(25);
      expect(screen.getByText("All the Way Down")).toBeInTheDocument();
      expect(screen.getByText("Kelela")).toBeInTheDocument();

      // Click the "delete pin" option in the first listen card
      const button = within(pinnedRecordings[0]).getByTitle("Delete Pin");
      await user.click(button);
      // Called with currentUser.auth_token and pin.row_id
      expect(deletePinSpy).toHaveBeenCalledWith("fnord", 100);
      // Wait for removePinFromPinsList to be called after a 1s setTimeout
      waitForElementToBeRemoved(pinnedRecordings[0]);
    });
  });
});
