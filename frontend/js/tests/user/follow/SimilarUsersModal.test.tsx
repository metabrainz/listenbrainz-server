import React from "react";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router";
import SimilarUsersModal from "../../../src/user/components/follow/SimilarUsersModal";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { ReactQueryWrapper } from "../../test-react-query";

const props = {
  user: { name: "shivam-kapila" },
  similarUsersList: [{ name: "mr_monkey", similarityScore: 0.567 }],
  loggedInUserFollowsUser: () => true,
  updateFollowingList: () => {},
};

const globalContext: GlobalAppContextT = {
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

const emptySimilarUsersProps = { ...props, similarUsersList: [] };
const currentUserGlobalContext = {
  ...globalContext,
  currentUser: { name: "shivam-kapila" },
};

describe("<SimilarUsersModal />", () => {
  it("renders the list of similar users", () => {
    render(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <SimilarUsersModal {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    expect(
      screen.getByRole("heading", { name: /Similar Users/i })
    ).toBeInTheDocument();
    const usernameButton = screen.getByRole("link", { name: "mr_monkey" });
    expect(usernameButton).toBeInTheDocument();
    expect(usernameButton).toHaveAttribute("href", "/user/mr_monkey/");
  });
  it("renders a compatibility score if logged in", () => {
    render(
      <GlobalAppContext.Provider value={currentUserGlobalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <SimilarUsersModal {...props} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toBeInTheDocument();
    // 0.567 gets rounded up to 57%
    expect(progressBar).toHaveAttribute("aria-valuenow", "57");
  });

  it("displays empty message when similarUsersList is empty for another user", () => {
    render(
      <GlobalAppContext.Provider value={globalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <SimilarUsersModal {...emptySimilarUsersProps} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    expect(
      screen.getByText(
        /Users with similar music tastes to shivam-kapila will appear here\./i
      )
    ).toBeInTheDocument();
  });

  it("displays empty message when similarUsersList is empty for the current user", () => {
    render(
      <GlobalAppContext.Provider value={currentUserGlobalContext}>
        <ReactQueryWrapper>
          <BrowserRouter>
            <SimilarUsersModal {...emptySimilarUsersProps} />
          </BrowserRouter>
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    expect(
      screen.getByText(
        /Users with similar music tastes to you will appear here\./i
      )
    ).toBeInTheDocument();
  });
});
