import * as React from "react";
import { render, screen } from "@testing-library/react";
import Loader from "../../src/components/Loader";

// To simplify testing, we mock 'react-loader-spinner' to render a simple, identifiable element.
jest.mock("react-loader-spinner", () => ({
  __esModule: true,
  default: () => <div data-testid="spinner" />,
}));

function ChildComponent() {
  return <div>Child Component</div>;
}

describe("Loader", () => {
  it('renders the spinner when "isLoading" is true', () => {
    render(
      <Loader isLoading>
        <ChildComponent />
      </Loader>
    );

    // Check that the spinner is visible
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    // Check that the children are not rendered
    expect(screen.queryByText("Child Component")).not.toBeInTheDocument();
  });

  it('renders its children when "isLoading" is false', () => {
    render(
      <Loader isLoading={false}>
        <ChildComponent />
      </Loader>
    );

    // Check that the children are visible
    expect(screen.getByText("Child Component")).toBeInTheDocument();
    // Check that the spinner is not rendered
    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("renders loaderText when provided and isLoading is true", () => {
    render(
      <Loader isLoading loaderText="Loading data...">
        <ChildComponent />
      </Loader>
    );

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.getByText("Loading data...")).toBeInTheDocument();
  });
});
