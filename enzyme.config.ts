/* eslint-disable import/no-extraneous-dependencies */
/* Used in jest.config.js */
import * as Enzyme from "enzyme";
import Adapter from "@cfaester/enzyme-adapter-react-18";
import { enableFetchMocks } from "jest-fetch-mock";

Enzyme.configure({ adapter: new Adapter() });


// In Node > v15 unhandled promise rejections will terminate the process
if (!process.env.LISTENING_TO_UNHANDLED_REJECTION) {
  process.on("unhandledRejection", (err) => {
    // eslint-disable-next-line no-console
    console.log("Unhandled promise rejection:", err);
  });
  // Avoid memory leak by adding too many listeners
  process.env.LISTENING_TO_UNHANDLED_REJECTION = "true";
}

window.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));
