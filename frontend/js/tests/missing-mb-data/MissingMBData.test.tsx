import * as React from "react";
import { mount } from "enzyme";

import { act } from "react-dom/test-utils";
import * as missingDataProps from "../__mocks__/missingMBDataProps.json";
import { youtube, spotify, user } from "../__mocks__/missingMBDataProps.json";

import MissingMBDataPage from "../../src/missing-mb-data/MissingMBData";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// // Mocking Math.random() fixes this
// // https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const props = {
  ...missingDataProps,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: user,
  },
};

describe("MissingMBDataPage", () => {
  it("renders the missing musicbrainz data page correctly", () => {
    const wrapper = mount<MissingMBDataPage>(
      <GlobalAppContext.Provider
        value={{ ...mountOptions.context, currentUser: props.user }}
      >
        <MissingMBDataPage {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });

  describe("handleClickPrevious", () => {
    beforeAll(() => {
      window.HTMLElement.prototype.scrollIntoView = jest.fn();
    });
    it("doesn't do anything if on the first page", async () => {
      const wrapper = mount<MissingMBDataPage>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: props.user }}
        >
          <MissingMBDataPage {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.afterDisplay = jest.fn();
      await act(() => {
        instance.handleClickPrevious();
      });

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currPage")).toEqual(1);
      expect(wrapper.state("totalPages")).toEqual(3);
      expect(wrapper.state("missingData")).toEqual(
        props.missingData.slice(0, 25)
      );
      expect(instance.afterDisplay).toHaveBeenCalledTimes(0);
    });

    it("goes to previous (first) page when on second page", async () => {
      const wrapper = mount<MissingMBDataPage>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: props.user }}
        >
          <MissingMBDataPage {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const afterDisplaySpy = jest.spyOn(instance, "afterDisplay");
      await act(() => {
        wrapper.setState({
          currPage: 2,
          missingData: props.missingData.slice(25, 50),
        });
      });

      await act(() => {
        instance.handleClickPrevious();
      });

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currPage")).toEqual(1);
      expect(wrapper.state("totalPages")).toEqual(3);
      expect(wrapper.state("missingData")).toEqual(
        props.missingData.slice(0, 25)
      );
      expect(afterDisplaySpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("handleClickNext", () => {
    beforeAll(() => {
      window.HTMLElement.prototype.scrollIntoView = jest.fn();
    });
    it("doesn't do anything if on the last page", async () => {
      const wrapper = mount<MissingMBDataPage>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: props.user }}
        >
          <MissingMBDataPage {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.afterDisplay = jest.fn();

      await act(() => {
        wrapper.setState({
          currPage: 3,
          missingData: props.missingData.slice(50, 73),
        });
      });

      await act(() => {
        instance.handleClickNext();
      });

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currPage")).toEqual(3);
      expect(wrapper.state("totalPages")).toEqual(3);
      expect(wrapper.state("missingData")).toEqual(
        props.missingData.slice(50, 73)
      );
      expect(instance.afterDisplay).toHaveBeenCalledTimes(0);
    });

    it("goes to next page when on first page", async () => {
      const wrapper = mount<MissingMBDataPage>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: props.user }}
        >
          <MissingMBDataPage {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const afterDisplaySpy = jest.spyOn(instance, "afterDisplay");

      await act(() => {
        instance.handleClickNext();
      });

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currPage")).toEqual(2);
      expect(wrapper.state("totalPages")).toEqual(3);
      expect(wrapper.state("missingData")).toEqual(
        props.missingData.slice(25, 50)
      );
      expect(afterDisplaySpy).toHaveBeenCalledTimes(1);
    });
  });
});
