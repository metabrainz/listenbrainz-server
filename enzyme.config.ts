/* eslint-disable import/no-extraneous-dependencies */
/* Used in jest.config.js */
import * as Enzyme from "enzyme";
import Adapter from "@cfaester/enzyme-adapter-react-18";
import { enableFetchMocks } from "jest-fetch-mock";

Enzyme.configure({ adapter: new Adapter() });

enableFetchMocks();
fetchMock.mockIf("https://coverartarchive.org/release").mockResponse(
  JSON.stringify({
    images: [
      {
        approved: true,
        back: false,
        comment: "",
        edit: 87011975,
        front: true,
        id: 31670459502,
        image:
          "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502.jpg",
        thumbnails: {
          "250":
            "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502-250.jpg",
          "500":
            "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502-500.jpg",
          "1200":
            "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502-1200.jpg",
          large:
            "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502-500.jpg",
          small:
            "http://coverartarchive.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8/31670459502-250.jpg",
        },
        types: ["Front"],
      },
    ],
    release:
      "https://musicbrainz.org/release/49a56e8b-2d89-423a-978c-6b24957b12a8",
  })
);

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
