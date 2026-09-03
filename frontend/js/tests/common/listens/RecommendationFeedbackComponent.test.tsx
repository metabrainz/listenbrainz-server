import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import RecommendationFeedbackComponent, {
  RecommendationFeedbackComponentProps,
} from "../../../src/common/listens/RecommendationFeedbackComponent";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import APIService from "../../../src/utils/APIService";

const mockAPIService = new APIService("");

const mockSubmitRecommendationFeedback = jest
  .spyOn(mockAPIService, "submitRecommendationFeedback")
  .mockResolvedValue(200);
const mockDeleteRecommendationFeedback = jest
  .spyOn(mockAPIService, "deleteRecommendationFeedback")
  .mockResolvedValue(200);

const listen: Listen = {
  listened_at: 0,
  playing_now: false,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
    additional_info: {
      recording_mbid: "some-recording-mbid",
      release_mbid: "some-release-mbid",
      recording_msid: "some-recording-msid",
      artist_mbids: ["xxxx"],
    },
  },
  user_name: "test",
};

const defaultProps: RecommendationFeedbackComponentProps = {
  listen,
  currentFeedback: null,
  updateFeedbackCallback: jest.fn(),
};

const defaultContext: Partial<GlobalAppContextT> = {
  currentUser: { auth_token: "test-token", name: "test" },
  APIService: mockAPIService,
};

// Helper function to render the component with necessary context
const renderComponent = (
  props: Partial<RecommendationFeedbackComponentProps> = {},
  context: Partial<GlobalAppContextT> = {}
) => {
  return render(
    <GlobalAppContext.Provider
      value={{ ...defaultContext, ...context } as GlobalAppContextT}
    >
      <RecommendationFeedbackComponent {...defaultProps} {...props} />
    </GlobalAppContext.Provider>
  );
};

const user = userEvent.setup();

describe("RecommendationFeedbackComponent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("submits new feedback when an option is clicked", async () => {
    renderComponent();

    await screen.findByTestId("recommendation-controls");
    // Open the dropdown
    await user.click(screen.getByRole("button", { expanded: false }));
    // Click the "Hate" option
    await user.click(
      screen.getByRole("button", { name: /i never want to hear this again/i })
    );

    expect(mockSubmitRecommendationFeedback).toHaveBeenCalledTimes(1);
    expect(mockSubmitRecommendationFeedback).toHaveBeenCalledWith(
      "test-token",
      "some-recording-mbid",
      "hate"
    );
    expect(defaultProps.updateFeedbackCallback).toHaveBeenCalledWith(
      "some-recording-mbid",
      "hate"
    );
  });

  it("deletes feedback when the currently selected option is clicked again", async () => {
    renderComponent({ currentFeedback: "love" });

    await screen.findByTestId("recommendation-controls");
    // Open the dropdown
    await user.click(screen.getByRole("button", { expanded: false }));
    // Click the "Love" option again
    await user.click(
      screen.getByRole("button", { name: /i really love this/i })
    );

    expect(mockDeleteRecommendationFeedback).toHaveBeenCalledTimes(1);
    expect(mockDeleteRecommendationFeedback).toHaveBeenCalledWith(
      "test-token",
      "some-recording-mbid"
    );
    expect(defaultProps.updateFeedbackCallback).toHaveBeenCalledWith(
      "some-recording-mbid",
      "love"
    );
  });

  it("does not render if user is not logged in", async () => {
    renderComponent(
      {},
      {
        currentUser: {
          name: "no-token",
          auth_token: undefined, //no auth token
        },
      }
    );
    expect(
      screen.queryByTestId("recommendation-controls")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { expanded: false })
    ).not.toBeInTheDocument();
  });

  it("does not update UI on API failure", async () => {
    mockSubmitRecommendationFeedback.mockRejectedValueOnce(
      new Error("API Error")
    );
    renderComponent();
    await screen.findByTestId("recommendation-controls");
    await user.click(screen.getByRole("button", { expanded: false }));
    await user.click(
      screen.getByRole("button", { name: /i never want to hear this again/i })
    );

    expect(mockSubmitRecommendationFeedback).toHaveBeenCalledTimes(1);
    // The callback should not be called if the API fails
    expect(defaultProps.updateFeedbackCallback).not.toHaveBeenCalled();
  });

  // Check the UI state for each feedback type
  const feedbackStates: Array<[
    RecommendationFeedBack | null,
    string,
    RegExp
  ]> = [
    ["love", "Love", /i really love this/i],
    ["like", "Like", /i like this/i],
    ["dislike", "Dislike", /i don't like this/i],
    ["hate", "Hate", /i never want to hear this again/i],
  ];

  it.each(feedbackStates)(
    "renders the correct UI for '%s' feedback",
    async (currentFeedback, buttonText, selectedTitle) => {
      renderComponent({ currentFeedback });
      await screen.findByTestId("recommendation-controls");
      // Check the main button's text
      expect(
        screen.getByRole("button", { expanded: false })
      ).toBeInTheDocument();

      // Open the dropdown and check which item is selected
      await user.click(
        // screen.getByRole("button", { name: new RegExp(buttonText, "i") })
        screen.getByRole("button", { name: buttonText })
      );
      const selectedItem = screen.getByRole("button", { name: selectedTitle });
      expect(selectedItem).toHaveClass("selected");
    }
  );
});
