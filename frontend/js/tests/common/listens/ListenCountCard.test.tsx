import * as React from "react";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import ListenCountCard from "../../../src/common/listens/ListenCountCard";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { render, screen } from "@testing-library/react";
import { textContentMatcher } from "../../test-utils/rtl-test-utils";

const user = {
  id: 1,
  name: "track_listener",
};

const loggedInUser = {
  id: 2,
  name: "iliekcomputers",
};

const globalContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  currentUser: loggedInUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

describe("ListenCountCard", () => {
  const originalToLocaleString = Number.prototype.toLocaleString;
  afterEach(() => {
    // Restore toLocaleString after each test to avoid test pollution
    Number.prototype.toLocaleString = originalToLocaleString;
  });
  it("renders correctly when listen count is not zero", () => {
    render(<ListenCountCard user={user} listenCount={100} />);

    expect(
      screen.getByText(/track_listener has listened to/i)
    ).toBeInTheDocument();
    expect(screen.getByText(textContentMatcher(/100/))).toBeInTheDocument();
    expect(screen.getByText(/songs so far/i)).toBeInTheDocument();
  });

  it("renders correctly when listen count is zero or undefined", () => {
    render(<ListenCountCard user={user} />);

    // Check for the specific text displayed when no listens are present
    expect(
      screen.getByText(/track_listener's listens count/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/track_listener hasn't listened to any songs yet./i)
    ).toBeInTheDocument();
  });

  it("renders large numbers formatted with locale", () => {
    // Force english locale
    Number.prototype.toLocaleString = jest.fn(function (this: Number) {
      const res = originalToLocaleString.call(this, "en");
      console.log("res", res);
      return res;
    });
    const { rerender } = render(
      <ListenCountCard user={user} listenCount={100000} />
    );
    expect(screen.getByText(/100,000/)).toBeInTheDocument();

    // Force Spanish locale and render again
    Number.prototype.toLocaleString = jest.fn(function (this: Number) {
      return originalToLocaleString.call(this, "es");
    });
    rerender(<ListenCountCard user={user} listenCount={100000} />);
    expect(screen.getByText(/100\.000/)).toBeInTheDocument();
  });

  it("renders user's name instead of 'You' when visiting another user's page", () => {
    render(
      <GlobalAppContext.Provider value={globalContext}>
        <ListenCountCard user={user} listenCount={100} />
      </GlobalAppContext.Provider>
    );

    // Assert that the user's name is present and "You" is not
    expect(
      screen.getByText(/track_listener has listened to/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/You have listened to/i)).not.toBeInTheDocument();
  });

  it("renders 'You' when on current user's page", () => {
    render(
      <GlobalAppContext.Provider value={globalContext}>
        <ListenCountCard user={loggedInUser} listenCount={100} />
      </GlobalAppContext.Provider>
    );

    // Assert that "You" is present and the user's name is not
    expect(screen.getByText(/You have listened to/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/iliekcomputers has listened to/i)
    ).not.toBeInTheDocument();
  });
});
