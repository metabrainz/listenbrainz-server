/* eslint-disable no-console */
import * as React from "react";
import { render, screen } from "@testing-library/react";

import userEvent from "@testing-library/user-event";
import ErrorBoundary from "../../src/utils/ErrorBoundary";

function ChildComponent() {
  return <div>Child Component</div>;
}

describe("ErrorBoundary", () => {
  const user = userEvent.setup();
  // Test component that throws an error
  const ThrowError = () => {
    throw new Error("Test error message");
  };

  // Temporarily suppress console errors so we don't clog the logs
  const realError = console.error;
  beforeEach(() => {
    jest.spyOn(global.console, "error");
    console.error = jest.fn();
  });
  afterEach(() => {
    console.error = realError;
  });

  it("renders error page correctly if child component throws error", () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText(/Test error message/i)).toBeInTheDocument();
    expect(screen.getByText(/Reload the page/i)).toBeInTheDocument();
  });

  it("reloads page when button is clicked", async () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    const reloadSpy = jest.fn();

    // Mock the reload function
    Object.defineProperty(window, "location", {
      value: {
        reload: reloadSpy,
      },
      writable: true,
    });

    const reloadButton = await screen.findByRole("button", {
      name: /reload the page/i,
    });
    await user.click(reloadButton);

    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("renders the child component if error is not thrown", () => {
    render(
      <ErrorBoundary>
        <ChildComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText(/Child Component/i)).toBeInTheDocument();
    expect(screen.queryByText(/Reload the page/i)).toBeNull();
  });
});
