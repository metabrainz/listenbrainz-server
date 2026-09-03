import * as React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { faHeart } from "@fortawesome/free-solid-svg-icons";
import ListenControl, {
  ListenControlProps,
} from "../../../src/common/listens/ListenControl";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const user = userEvent.setup();

const defaultProps: ListenControlProps = {
  title: "foobar title",
  text: "foobar text",
  icon: faHeart,
};

describe("ListenControl", () => {
  it("renders as a button by default", () => {
    renderWithProviders(<ListenControl {...defaultProps} />);
    const button = screen.getByRole("menuitem");

    expect(button).toBeInTheDocument();
    expect(button.tagName).toBe("BUTTON");
    expect(button).toHaveTextContent("foobar text");
    expect(button).toHaveAttribute("title", "foobar title");
  });

  it("renders as a link when 'link' prop is provided", () => {
    renderWithProviders(<ListenControl {...defaultProps} link="https://example.com" />);
    const link = screen.getByRole("link", { name: "foobar title" });

    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveTextContent("foobar text");
  });

  it("calls the action handler when the button is clicked", async () => {
    const handleClick = jest.fn();

    renderWithProviders(<ListenControl {...defaultProps} action={handleClick} />);

    await user.click(screen.getByRole("menuitem"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when the 'disabled' prop is true", async () => {
    const handleClick = jest.fn();
    renderWithProviders(<ListenControl {...defaultProps} action={handleClick} disabled />);

    const button = screen.getByRole("menuitem");
    expect(button).toBeDisabled();

    await user.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("renders with 'dropdown-item' class by default", () => {
    renderWithProviders(<ListenControl {...defaultProps} />);
    expect(screen.getByRole("menuitem")).toHaveClass("dropdown-item");
  });

  it("renders without 'dropdown-item' class when isDropdown is false", () => {
    renderWithProviders(<ListenControl {...defaultProps} isDropdown={false} />);
    expect(screen.getByRole("menuitem")).not.toHaveClass("dropdown-item");
  });
});
