/* eslint-disable jest/no-disabled-tests */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import * as React from "react";
import { BrowserRouter } from "react-router-dom";
import HueSound from "../../../src/explore/huesound/HueSound";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";

const release: ColorReleaseItem = {
  artist_name: "Letherette",
  color: [250, 90, 192],
  dist: 109.973,
  release_mbid: "00a109da-400c-4350-9751-6e6f25e89073",
  caa_id: 34897349734,
  release_name: "EP5",
  recordings: [],
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
// const queryKey = ["huesound", {}];
// queryClient.setQueryDefaults(queryKey, {
//   queryFn: () => ({  }),
// });

const reactQueryWrapper = ({ children }: any) => (
  <BrowserRouter>
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  </BrowserRouter>
);

const user = userEvent.setup();

describe("HueSound", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    // Mock the server responses
    const handlers = [
      // http.post("/", () => {
      //   // return feed events
      //   return HttpResponse.json({ events: timelineProps.events });
      // }),
      http.get("/1//explore/color/.getContext('2d')", () =>
        HttpResponse.json({ payload: { releases: [release] } })
      ),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  afterAll(() => {
    server.close();
  });

  it("contains a ColorWheel instance", () => {
    renderWithProviders(
      <HueSound />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );
    screen.getByTestId("colour-picker");
    screen.getByText(textContentMatcher("Choose a color"));
  });

  it("renders a release when selected", async () => {
    renderWithProviders(
      <HueSound />,
      {},
      {
        wrapper: reactQueryWrapper,
      }
    );

    const canvasElement = screen.getByTestId("colour-picker");
    console.log(canvasElement)
    await user.click(canvasElement);
    screen.getByText(textContentMatcher("EP5"));
  }, 5000);
  // xdescribe("selectRelease", () => {
  // it("selects the particular release and starts playing it in brainzplayer", async () => {
  //   const wrapper = mount<ColorPlay>(<ColorPlay {...props} />, mountOptions);
  //   const instance = wrapper.instance();
  // });
  // });
});
