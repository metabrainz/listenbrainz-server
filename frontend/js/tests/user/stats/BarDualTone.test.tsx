import * as React from "react";
import { render, screen } from "@testing-library/react";

import BarDualTone from "../../../src/user/stats/components/BarDualTone";
import * as ListeningActivityDataWeek from "../../__mocks__/userListeningActivityProcessDataWeek.json";
import * as ListeningActivityDataMonth from "../../__mocks__/userListeningActivityProcessDataMonth.json";
import * as ListeningActivityDataYear from "../../__mocks__/userListeningActivityProcessDataYear.json";
import * as ListeningActivityDataAllTime from "../../__mocks__/userListeningActivityProcessDataAllTime.json";
import { ResponsiveBar } from "@nivo/bar";
import { COLOR_LB_BLUE } from "../../../src/utils/constants";

// Mocking the ResponsiveBar component to inspect the props it receives
jest.mock("@nivo/bar", () => ({
  ResponsiveBar: jest.fn(() => null),
}));

const mockResponsiveBar = ResponsiveBar as jest.Mock;

describe("BarDualTone", () => {
  // Clear mocks before each test to ensure isolation
  beforeEach(() => {
    mockResponsiveBar.mockClear();
  });

  const baseProps = {
    thisRangePeriod: { start: 1591574400, end: 1592092800 },
    lastRangePeriod: { start: 1590969600, end: 1591488000 },
  };

  it("renders correctly and passes the right props for the 'week' range", () => {
    render(
      <BarDualTone
        {...baseProps}
        data={ListeningActivityDataWeek}
        range="week"
        showLegend
      />
    );

    expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    // Check that ResponsiveBar was called with the correct props for 'week'
    expect(mockResponsiveBar).toHaveBeenCalledWith(
      expect.objectContaining({
        data: ListeningActivityDataWeek,
        keys: ["lastRangeCount", "thisRangeCount"],
        groupMode: "grouped",
      }),
      {}
    );
  });

  it("renders correctly and passes the right props for the 'month' range", () => {
    render(
      <BarDualTone
        {...baseProps}
        data={ListeningActivityDataMonth}
        range="month"
        showLegend
      />
    );

    expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    expect(mockResponsiveBar).toHaveBeenCalledWith(
      expect.objectContaining({
        data: ListeningActivityDataMonth,
        keys: ["lastRangeCount", "thisRangeCount"],
      }),
      {}
    );
  });

  it("renders correctly and passes the right props for the 'year' range", () => {
    render(
      <BarDualTone
        {...baseProps}
        data={ListeningActivityDataYear}
        range="year"
        showLegend
      />
    );

    expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    expect(mockResponsiveBar).toHaveBeenCalledWith(
      expect.objectContaining({
        data: ListeningActivityDataYear,
        keys: ["lastRangeCount", "thisRangeCount"],
      }),
      {}
    );
  });

  it("renders correctly and passes the right props for the 'all_time' range", () => {
    render(
      <BarDualTone
        thisRangePeriod={{}}
        lastRangePeriod={{}}
        data={ListeningActivityDataAllTime}
        range="all_time"
      />
    );

    expect(screen.getByTestId("listening-activity-bar")).toBeInTheDocument();
    // For 'all_time', only one key should be passed to the chart
    expect(mockResponsiveBar).toHaveBeenCalledWith(
      expect.objectContaining({
        data: ListeningActivityDataAllTime,
        keys: ["thisRangeCount"],
      }),
      {}
    );
  });

  describe("previous period colour", () => {
    const getLastRangeColors = () => {
      const { colors, legends } = mockResponsiveBar.mock.calls[0][0];
      return {
        bar: colors({ id: "lastRangeCount" }),
        legend: legends[0].data[0].color,
      };
    };

    afterEach(() => {
      delete document.documentElement.dataset.bsTheme;
    });

    it("uses the brand blue in the light theme", () => {
      render(
        <BarDualTone
          {...baseProps}
          data={ListeningActivityDataWeek}
          range="week"
          showLegend
        />
      );
      expect(getLastRangeColors()).toEqual({
        bar: COLOR_LB_BLUE,
        legend: COLOR_LB_BLUE,
      });
    });

    it("uses a lighter purple in the dark theme so the bars stay visible", () => {
      document.documentElement.dataset.bsTheme = "dark";
      render(
        <BarDualTone
          {...baseProps}
          data={ListeningActivityDataWeek}
          range="week"
          showLegend
        />
      );
      const { bar, legend } = getLastRangeColors();
      expect(bar).not.toEqual(COLOR_LB_BLUE);
      expect(legend).toEqual(bar);
    });
  });
});
