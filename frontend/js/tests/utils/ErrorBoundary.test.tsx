import * as React from "react";
import { mount } from "enzyme";

import ErrorBoundary from "../../src/utils/ErrorBoundary";

function ChildComponent() {
  return <div>Child Component</div>;
}

describe("ErrorBoundary", () => {
  it("renders error page correctly if child component throws error", () => {
    const wrapper = mount(
      <ErrorBoundary>
        <ChildComponent />
      </ErrorBoundary>
    );

    wrapper.find(ChildComponent).simulateError(Error("Test Error"));

    expect(wrapper.state()).toMatchObject({ hasError: true });
    expect(wrapper).toMatchSnapshot();
  });

  it("reloads page when button is clicked", () => {
    const wrapper = mount(
      <ErrorBoundary>
        <ChildComponent />
      </ErrorBoundary>
    );

    wrapper.find(ChildComponent).simulateError(Error("Test Error"));
    // Mock the reload function
    Object.defineProperty(window, "location", {
      value: {
        reload: jest.fn(),
      },
      writable: true,
    });
    wrapper.find("button").simulate("click");

    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });

  it("renders the child component if error is not thrown", () => {
    const wrapper = mount(
      <ErrorBoundary>
        <ChildComponent />
      </ErrorBoundary>
    );

    expect(wrapper.state()).toMatchObject({ hasError: false });
    expect(wrapper).toMatchSnapshot();
  });
});
