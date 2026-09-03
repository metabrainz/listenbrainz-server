import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NamePill from "../../src/personal-recommendations/NamePill";

describe("NamePill", () => {
  it("renders the title and a close button when a closeAction is provided", () => {
    const mockCloseAction = jest.fn();
    render(<NamePill title="Test User" closeAction={mockCloseAction} />);

    // Check for the title text
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByTitle("Remove")).toBeInTheDocument();
  });

  it("does not render a close button if closeAction is not provided", () => {
    render(<NamePill title="Test User" />);

    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /remove/i })
    ).not.toBeInTheDocument();
  });

  it("calls the closeAction handler when the close button is clicked", async () => {
    const mockCloseAction = jest.fn();
    const user = userEvent.setup();
    render(<NamePill title="Test User" closeAction={mockCloseAction} />);

    const closeButton = screen.getByTitle("Remove");
    await user.click(closeButton);

    expect(mockCloseAction).toHaveBeenCalledTimes(1);
  });
});
