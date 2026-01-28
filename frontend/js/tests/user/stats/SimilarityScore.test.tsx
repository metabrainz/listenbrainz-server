import * as React from "react";
import { render, screen } from "@testing-library/react";
import SimilarityScore, {
  SimilarityScoreProps,
} from "../../../src/user/components/follow/SimilarityScore";

const defaultProps: SimilarityScoreProps = {
  similarityScore: 0.239745792, // This will be rounded to 24%
  user: { auth_token: "baz", name: "test" },
  type: "regular",
};

describe("SimilarityScore", () => {
  it("renders correctly for type = 'regular'", () => {
    render(<SimilarityScore {...defaultProps} />);

    // Check for the progress bar by its accessible role
    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toBeInTheDocument();

    // Check that the correct value is set for accessibility
    expect(progressBar).toHaveAttribute("aria-valuenow", "24");

    // Check for the descriptive text associated with the 'regular' type
    expect(
      screen.getByText("Your compatibility with test is 24%")
    ).toBeInTheDocument();
  });

  it("renders correctly for type = 'compact'", () => {
    render(<SimilarityScore {...defaultProps} type="compact" />);

    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute("aria-valuenow", "24");

    // In compact mode, only the percentage is shown
    expect(screen.getByText("24%")).toBeInTheDocument();
    // The descriptive text should not be present
    expect(
      screen.queryByText(/Your compatibility with/)
    ).not.toBeInTheDocument();
  });

  it("updates the progress bar color based on the similarity score", () => {
    const { rerender } = render(
      <SimilarityScore {...defaultProps} similarityScore={0.25} />
    );

    const progressBar = screen.getByRole("progressbar");
    // The class is on the inner div of the progress bar element
    expect(progressBar.firstChild).toHaveClass("orange");

    rerender(<SimilarityScore {...defaultProps} similarityScore={0.15} />);
    expect(progressBar.firstChild).toHaveClass("red");

    rerender(<SimilarityScore {...defaultProps} similarityScore={0.6} />);
    expect(progressBar.firstChild).toHaveClass("purple");

    rerender(<SimilarityScore {...defaultProps} similarityScore={0.3} />);
    expect(progressBar.firstChild).toHaveClass("orange");
  });
});
