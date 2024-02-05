import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import BarDualTone from "../../../src/user/stats/components/BarDualTone";
import * as ListeningActivityDataWeek from "../../__mocks__/userListeningActivityProcessDataWeek.json";
import * as ListeningActivityDataMonth from "../../__mocks__/userListeningActivityProcessDataMonth.json";
import * as ListeningActivityDataYear from "../../__mocks__/userListeningActivityProcessDataYear.json";
import * as ListeningActivityDataAllTime from "../../__mocks__/userListeningActivityProcessDataAllTime.json";
import { ResponsiveBar } from "@nivo/bar";

describe("BarDualTone", () => {
  it("renders correctly for week", () => {
    const wrapper = mount(
      <div style={{ width: 400, height: 225 }}>
        <BarDualTone
          data={ListeningActivityDataWeek}
          range="week"
          thisRangePeriod={{ start: 1591574400, end: 1592092800 }}
          lastRangePeriod={{ start: 1590969600, end: 1591488000 }}
          showLegend
        />
      </div>
    );
    expect(wrapper.find(ResponsiveBar)).toHaveLength(1);
  });

  it("renders correctly for month", () => {
    const wrapper = mount(
      <div style={{ width: 400, height: 225 }}>
        <BarDualTone
          data={ListeningActivityDataMonth}
          range="month"
          thisRangePeriod={{ start: 1590969600 }}
          lastRangePeriod={{ start: 1588291200 }}
          showLegend
        />
      </div>
    );
    expect(wrapper.find(ResponsiveBar)).toHaveLength(1);
  });

  it("renders correctly for year", () => {
    const wrapper = mount(
      <div style={{ width: 400, height: 225 }}>
        <BarDualTone
          data={ListeningActivityDataYear}
          range="month"
          thisRangePeriod={{ start: 1577836800 }}
          lastRangePeriod={{ start: 1546300800 }}
          showLegend
        />
      </div>
    );
    expect(wrapper.find(ResponsiveBar)).toHaveLength(1);
  });

  it("renders correctly for all_time", () => {
    const wrapper = mount(
      <div style={{ width: 400, height: 225 }}>
        <BarDualTone
          data={ListeningActivityDataAllTime}
          range="month"
          thisRangePeriod={{}}
          lastRangePeriod={{}}
        />
      </div>
    );
    expect(wrapper.find(ResponsiveBar)).toHaveLength(1);
  });
});
