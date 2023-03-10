import * as React from "react";
import { mount } from "enzyme";

import Loader from "../../src/components/Loader";

function ChildComponent() {
  return <div>Child Component</div>;
}

describe("Loader", () => {
  it('renders loader when "isLoading" is true', () => {
    const wrapper = mount(
      <Loader isLoading>
        <ChildComponent />
      </Loader>
    );

    expect(wrapper).toMatchSnapshot();
  });

  it('renders child component when "isLoading" is false', () => {
    const wrapper = mount(
      <Loader isLoading={false}>
        <ChildComponent />
      </Loader>
    );

    expect(wrapper).toMatchSnapshot();
  });
});
