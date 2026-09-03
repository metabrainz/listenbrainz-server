import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { faMeh } from "@fortawesome/free-solid-svg-icons";
import { faMeh as faMehRegular } from "@fortawesome/free-regular-svg-icons";
import RecommendationControl, {
  RecommendationControlProps,
} from "../../src/user/recommendations/components/RecommendationControl";

const props: RecommendationControlProps = {
  cssClass: "bad_recommendation",
  // Use jest.fn() for the action prop to spy on calls
  action: jest.fn(),
  iconHover: faMeh,
  icon: faMehRegular,
  title: "This is a bad recommendation",
};

describe("RecommendationControl", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders correctly with provided props", () => {
    render(<RecommendationControl {...props} />);

    const recommendationControl = screen.getByRole("button", {
      name: "This is a bad recommendation",
    });
    expect(recommendationControl).toHaveClass("recommendation-icon");
    expect(recommendationControl).toHaveClass("bad_recommendation");
  });

  it("calls the action prop when clicked", async () => {
    render(<RecommendationControl {...props} />);

    const recommendationControl = screen.getByRole("button", {
      name: "This is a bad recommendation",
    });
    await userEvent.click(recommendationControl);

    expect(props.action).toHaveBeenCalledTimes(1);
  });

  it("calls the action prop when pressed on mobile devices", async () => {
    render(<RecommendationControl {...props} />);

    const recommendationControl = screen.getByRole("button", {
      name: "This is a bad recommendation",
    });
    // Should work on mobile devices
    await userEvent.pointer({
      keys: "[TouchA]",
      target: recommendationControl,
    });
    expect(props.action).toHaveBeenCalledTimes(1);
  });
});
