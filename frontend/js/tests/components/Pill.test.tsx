import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Pill from "../../src/components/Pill";

describe("Pill", () => {
  it("renders correctly with default props", () => {
    render(<Pill>Test Pill</Pill>);
    const pillButton = screen.getByRole("button", { name: /test pill/i });

    expect(pillButton).toBeInTheDocument();
    expect(pillButton).toHaveClass("pill");
    expect(pillButton).not.toHaveClass("active");
    expect(pillButton).not.toHaveClass("secondary");
  });

  it("applies the 'active' class when the active prop is true", () => {
    render(<Pill active>Active Pill</Pill>);
    const pillButton = screen.getByRole("button", { name: /active pill/i });
    expect(pillButton).toHaveClass("pill", "active");
  });

  it("applies the 'primary' or 'secondary' class dependinjg on the 'type' prop", () => {
    const { rerender } = render(<Pill type="secondary">Secondary Pill</Pill>);
    let pillButton = screen.getByRole("button", { name: /secondary pill/i });
    expect(pillButton).toHaveClass("pill", "secondary");
    // Change the prop, rerender and check the applied CSS class (no 'primary' nor 'secondary' class)
    rerender(<Pill type="primary">Primary Pill</Pill>);
    pillButton = screen.getByRole("button", { name: /primary pill/i });
    expect(pillButton).toHaveClass("pill");
    expect(pillButton).not.toHaveClass("secondary");
  });

  it("applies both 'active' and 'secondary' classes when both props are set", () => {
    render(
      <Pill active type="secondary">
        Active Secondary
      </Pill>
    );
    const pillButton = screen.getByRole("button", {
      name: /active secondary/i,
    });
    expect(pillButton).toHaveClass("pill", "secondary", "active");
  });

  it("calls the onClick handler when clicked", async () => {
    const handleClick = jest.fn();
    const user = userEvent.setup();
    render(<Pill onClick={handleClick}>Clickable</Pill>);

    await user.click(screen.getByRole("button", { name: /clickable/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
