import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router";
import FollowerFollowingModal, {
  FollowerFollowingModalProps,
} from "../../../src/user/components/follow/FollowerFollowingModal";
import APIService from "../../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../../test-react-query";
import { textContentMatcher } from "../../test-utils/rtl-test-utils";

const defaultProps: FollowerFollowingModalProps = {
  user: { name: "foobar" },
  followerList: ["foo"],
  followingList: ["bar"],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};

const defaultContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {},
  spotifyAuth: {},
  currentUser: {} as ListenBrainzUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};
// Helper function to render the component with all necessary providers.
const renderComponent = (
  props: Partial<FollowerFollowingModalProps> = {},
  context: Partial<GlobalAppContextT> = {}
) => {
  return render(
    <GlobalAppContext.Provider value={{ ...defaultContext, ...context }}>
      <ReactQueryWrapper>
        <BrowserRouter>
          <FollowerFollowingModal {...defaultProps} {...props} />
        </BrowserRouter>
      </ReactQueryWrapper>
    </GlobalAppContext.Provider>
  );
};

describe("<FollowerFollowingModal />", () => {
  it("renders with initial following list", () => {
    renderComponent();

    // Check if the "Following" pill is active and the user from followingList is present
    expect(
      screen.getByRole("button", { name: /Following \(1\)/i })
    ).toHaveClass("active");
    expect(screen.getByText("bar")).toBeInTheDocument();
    // Ensure follower is not present in this view
    expect(screen.queryByText("foo")).not.toBeInTheDocument();
  });

  it("updates the mode correctly when clicking on pills", async () => {
    renderComponent();

    // Initial state: "following" is active
    expect(
      screen.getByRole("button", { name: /Following \(1\)/i })
    ).toHaveClass("active");
    expect(screen.getByText("bar")).toBeInTheDocument();

    // Click on "Followers" pill
    await userEvent.click(
      screen.getByRole("button", { name: /Followers \(1\)/i })
    );

    // Wait for the state to update and the component to re-render
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Followers \(1\)/i })
      ).toHaveClass("active");
      expect(screen.getByText("foo")).toBeInTheDocument();
      expect(screen.queryByText("bar")).not.toBeInTheDocument();
    });

    // Click on "Following" pill again
    await userEvent.click(
      screen.getByRole("button", { name: /Following \(1\)/i })
    );

    // Wait for the state to update and the component to re-render
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Following \(1\)/i })
      ).toHaveClass("active");
      expect(screen.getByText("bar")).toBeInTheDocument();
      expect(screen.queryByText("foo")).not.toBeInTheDocument();
    });
  });

  it("displays correct message when follower list is empty", async () => {
    renderComponent({ followerList: [] });

    // Click on "Followers" pill
    await userEvent.click(
      screen.getByRole("button", { name: /Followers \(0\)/i })
    );

    expect(
      screen.getByText(
        textContentMatcher(/foobar doesn't have any followers\./i)
      )
    ).toBeInTheDocument();
  });

  it("displays correct message when following list is empty", () => {
    renderComponent({ followingList: [] });

    // "Following" is active by default
    expect(
      screen.getByText(/foobar isn't following anyone\./i)
    ).toBeInTheDocument();
  });

  it("displays correct message for current user when follower list is empty", async () => {
    renderComponent(
      { followerList: [] },
      {
        currentUser: { name: "foobar" },
      }
    );

    // Click on "Followers" pill
    await userEvent.click(
      screen.getByRole("button", { name: /Followers \(0\)/i })
    );

    expect(
      screen.getByText(/You don't have any followers\./i)
    ).toBeInTheDocument();
  });

  it("displays correct message for current user when following list is empty", () => {
    renderComponent(
      { followingList: [] },
      {
        currentUser: { name: "foobar" },
      }
    );

    // "Following" is active by default
    expect(
      screen.getByText(/You aren't following anyone\./i)
    ).toBeInTheDocument();
  });
});
