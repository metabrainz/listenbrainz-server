import * as React from "react";
import { mount, shallow } from "enzyme";

import { act } from "react-dom/test-utils";
import LibreFMImporterModal from "../../src/lastfm/LibreFMImporterModal";

const props = {
  disable: false,
  children: [],
  onClose: (event: React.MouseEvent<HTMLButtonElement>) => {},
};

describe("LibreFMImporterModal", () => {
  it("renders", () => {
    const wrapper = mount(<LibreFMImporterModal {...props} />);
    expect(wrapper.find("#listen-progress-container")).toHaveLength(1);
    expect(wrapper.find("button")).toHaveLength(1);
  });

  it("close button is disabled/enabled based upon props", async () => {
    const wrapper = shallow(<LibreFMImporterModal {...props} />);
    // Test if close button is disabled
    await act(() => {
      wrapper.setProps({ disable: true });
    });
    expect(wrapper.find("button").props().disabled).toBe(true);

    // Test if close button is enabled
    await act(() => {
      wrapper.setProps({ disable: false });
    });
    expect(wrapper.find("button").props().disabled).toBe(false);
  });
});
