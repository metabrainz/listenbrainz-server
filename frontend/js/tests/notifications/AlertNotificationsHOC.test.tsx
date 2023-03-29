import * as React from "react";
import { shallow, mount } from "enzyme";
import { act } from "react-dom/test-utils";
import { withAlertNotifications } from "../../src/notifications/AlertNotificationsHOC";
import { waitForComponentToPaint } from "../test-utils";

const fakeComponent = function FakeComponent() {
  return <div />;
};

describe("AlertNotifications higher-order component", () => {
  beforeAll(() => {
    // For alert id
    jest.spyOn(Date.prototype, "getTime").mockImplementation(() => 0);
  });
  afterAll(() => {
    jest.restoreAllMocks();
  });

  it("renders alerts on screen with the correct css classname", () => {
    const WrappedComponent = withAlertNotifications(fakeComponent);
    const fakeAlerts = [
      {
        id: 0,
        type: "warning" as AlertType,
        headline: "Test",
        message: "Have you seen the Fnords?",
        count: 1,
      },
      {
        id: 1,
        type: "danger" as AlertType,
        headline: "Oh no!",
        message: "The foo hit the bar",
        count: 1,
      },
      {
        id: 2,
        type: "success" as AlertType,
        headline: "Oh yeah!",
        message: "Time for *us* to hit the bar",
        count: 1,
      },
    ];
    const wrapper = mount<React.ComponentType>(
      <WrappedComponent initialAlerts={fakeAlerts} />
    );

    expect(wrapper.find(".alert")).toHaveLength(3);
    expect(wrapper.find(".alert").at(0).hasClass("alert-warning")).toBeTruthy();
    expect(wrapper.find(".alert").at(0).find("h4").text()).toEqual("Test");
    expect(
      wrapper.find(".alert").at(0).contains("Have you seen the Fnords?")
    ).toBeTruthy();

    expect(wrapper.find(".alert").at(1).hasClass("alert-danger")).toBeTruthy();
    expect(
      wrapper.find(".alert").at(1).contains("The foo hit the bar")
    ).toBeTruthy();

    expect(wrapper.find(".alert").at(2).hasClass("alert-success")).toBeTruthy();
    expect(
      wrapper.find(".alert").at(2).contains("Time for *us* to hit the bar")
    ).toBeTruthy();
  });

  describe("newAlert", () => {
    it("creates a new alert", async () => {
      const WrappedComponent = withAlertNotifications(fakeComponent);
      const wrapper = shallow<React.ComponentType>(<WrappedComponent />);
      const instance = wrapper.instance();

      expect(wrapper.state().alerts).toEqual([]);
      await act(() => {
        (instance as any).newAlert("warning", "Test", "foobar");
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state().alerts).toEqual([
        {
          id: 0,
          type: "warning",
          headline: "Test",
          message: "foobar",
          count: undefined,
        },
      ]);
    });
    it("doesn't create a new alert but increments count if passed same alert", async () => {
      const WrappedComponent = withAlertNotifications(fakeComponent);
      const wrapper = shallow<React.ComponentType>(<WrappedComponent />);
      const instance = wrapper.instance();

      expect(wrapper.state().alerts).toEqual([]);
      await act(() => {
        (instance as any).newAlert("warning", "Test", "foobar");
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state().alerts).toEqual([
        {
          id: 0,
          type: "warning",
          headline: "Test",
          message: "foobar",
          count: undefined,
        },
      ]);
      await act(() => {
        (instance as any).newAlert("danger", "test", <p>foobar</p>);
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state().alerts).toEqual([
        {
          id: 0,
          type: "warning",
          headline: "Test",
          message: "foobar",
          count: undefined,
        },
        {
          id: 0,
          type: "danger",
          headline: "test",
          message: <p>foobar</p>,
        },
      ]);
      await act(() => {
        (instance as any).newAlert("warning", "Test", "foobar");
      });
      await act(() => {
        (instance as any).newAlert("warning", "Test", "foobar");
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state().alerts).toEqual([
        {
          id: 0,
          type: "warning",
          headline: "Test (3)",
          message: "foobar",
          count: 3,
        },
        {
          id: 0,
          type: "danger",
          headline: "test",
          message: <p>foobar</p>,
        },
      ]);
    });
    it("creates a new alert from child component", async () => {
      const WrappedComponent = withAlertNotifications(fakeComponent);
      const wrapper = shallow<React.ComponentType>(<WrappedComponent />);
      const instance = wrapper.instance();

      const childComponent: any = wrapper.find(fakeComponent);

      expect(wrapper.state().alerts).toEqual([]);
      expect(childComponent).toBeDefined();

      expect(childComponent.props().newAlert).toBeDefined();
      await act(() => {
        childComponent.props().newAlert("warning", "Test", "foobar");
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state().alerts).toEqual([
        { id: 0, type: "warning", headline: "Test", message: "foobar" },
      ]);
    });
  });

  describe("onAlertDismissed", () => {
    it("deletes an alert", async () => {
      const WrappedComponent = withAlertNotifications(fakeComponent);
      const wrapper = mount<React.ComponentType>(<WrappedComponent />);
      const instance = wrapper.instance();

      const alert1 = {
        id: 0,
        type: "warning",
        headline: "Test",
        message: "foobar",
      } as Alert;
      const alert2 = {
        id: 0,
        type: "danger",
        headline: "test",
        message: <p>foobar</p>,
      } as Alert;
      await act(() => {
        wrapper.setState({
          alerts: [alert1, alert2],
        });
      });
      expect(wrapper.state().alerts).toEqual([alert1, alert2]);
      await act(() => {
        (instance as any).onAlertDismissed(alert1);
      });
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state().alerts).toEqual([alert2]);

      // Click on the close (x) button
      expect(wrapper.find(".alert").at(0).childAt(0).type()).toEqual("button");
      wrapper.find(".alert").at(0).childAt(0).simulate("click");
      expect(wrapper.state().alerts).toEqual([]);
    });
  });
});
