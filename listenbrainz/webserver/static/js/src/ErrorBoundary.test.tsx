import * as React from "react";
import { mount } from "enzyme";

import ErrorBoundary from "./ErrorBoundary";

const ChildComponent = () => {
  return <div>Child Component</div>;
};

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
