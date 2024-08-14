import * as React from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import { SetupServerApi, setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import UserTopEntity, {
  UserTopEntityProps,
} from "../../../src/user/stats/components/UserTopEntity";
import * as userArtists from "../../__mocks__/userArtists.json";
import * as userReleases from "../../__mocks__/userReleases.json";
import * as userRecordings from "../../__mocks__/userRecordings.json";
import * as userReleaseGroups from "../../__mocks__/userReleaseGroups.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const userProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  terminology: "artist",
  user: {
    name: "test_user",
  },
};

const sitewideProps: UserTopEntityProps = {
  range: "week",
  entity: "artist",
  terminology: "artist",
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe.each([
  ["User Stats", userProps],
  ["Sitewide Stats", sitewideProps],
])("%s", (name, props) => {
  describe("UserTopEntity", () => {
    let server: SetupServerApi;
    beforeAll(async () => {
      const handlers = [
        http.get("/1/stats/user/test_user/artists", async (path) => {
          return HttpResponse.json(userArtists);
        }),
        http.get("/1/stats/user/test_user/releases", async (path) => {
          return HttpResponse.json(userReleases);
        }),
        http.get("/1/stats/user/test_user/release-groups", async (path) => {
          return HttpResponse.json(userReleaseGroups);
        }),
        http.get("/1/stats/user/test_user/recordings", async (path) => {
          return HttpResponse.json(userRecordings);
        }),
      ];
      const sitewideHandlers = [
        http.get("/`1/stats/sitewide/artists", async (path) => {
          return HttpResponse.json(userArtists);
        }),
        http.get("/1/stats/sitewide/releases", async (path) => {
          return HttpResponse.json(userReleases);
        }),
        http.get("/1/stats/sitewide/release-groups", async (path) => {
          return HttpResponse.json(userReleaseGroups);
        }),
        http.get("/1/stats/sitewide/recordings", async (path) => {
          return HttpResponse.json(userRecordings);
        }),
      ];
      server = setupServer(...handlers, ...sitewideHandlers);
      server.listen();
    });
    afterEach(() => {
      queryClient.cancelQueries();
      queryClient.clear();
    });
    it("renders correctly for artist", async () => {
      const queryKey = ["user-top-entity", "artist", "week", props.user?.name];
      queryClient.ensureQueryData({
        queryKey,
        queryFn: () => {
          return {
            data: userArtists,
            loading: false,
            hasError: false,
            errorMessage: "",
          };
        },
      });
      renderWithProviders(
        <UserTopEntity {...props} />,
        {},
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        expect(screen.getByTestId("top-artist-list")).toBeInTheDocument();
      });

      expect(screen.getByTestId("top-artist")).toBeInTheDocument();
      expect(screen.getByText("Top artists")).toBeInTheDocument();
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });

    it("renders correctly for release", async () => {
      const queryKey = ["user-top-entity", "release", "week", props.user?.name];
      queryClient.ensureQueryData({
        queryKey,
        queryFn: () => {
          return {
            data: userReleases,
            loading: false,
            hasError: false,
            errorMessage: "",
          };
        },
      });
      renderWithProviders(
        <UserTopEntity {...props} entity="release" terminology="release" />,
        {},
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        expect(screen.getByTestId("top-release-list")).toBeInTheDocument();
      });

      expect(screen.getByTestId("top-release")).toBeInTheDocument();
      expect(screen.getByText("Top releases")).toBeInTheDocument();
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });

    it("renders correctly for release group", async () => {
      const queryKey = [
        "user-top-entity",
        "release-group",
        "week",
        props.user?.name,
      ];
      queryClient.ensureQueryData({
        queryKey,
        queryFn: () => {
          return {
            data: userReleaseGroups,
            loading: false,
            hasError: false,
            errorMessage: "",
          };
        },
      });
      renderWithProviders(
        <UserTopEntity
          {...props}
          entity="release-group"
          terminology="release group"
        />,
        {},
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("top-release-group-list")
        ).toBeInTheDocument();
      });

      expect(screen.getByTestId("top-release-group")).toBeInTheDocument();
      expect(screen.getByText("Top release groups")).toBeInTheDocument();
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });

    it("renders correctly for recording", async () => {
      const queryKey = [
        "user-top-entity",
        "recording",
        "week",
        props.user?.name,
      ];
      queryClient.ensureQueryData({
        queryKey,
        queryFn: () => {
          return {
            data: userRecordings,
            loading: false,
            hasError: false,
            errorMessage: "",
          };
        },
      });
      renderWithProviders(
        <UserTopEntity {...props} entity="recording" terminology="track" />,
        {},
        {
          wrapper: reactQueryWrapper,
        }
      );

      await waitFor(() => {
        expect(screen.getByTestId("top-recording-list")).toBeInTheDocument();
      });

      expect(screen.getByTestId("top-recording")).toBeInTheDocument();
      expect(screen.getByText("Top tracks")).toBeInTheDocument();
      expect(screen.getAllByTestId("listen")).toHaveLength(25);
    });

    it("displays error message when API call fails", async () => {
      const errorMessage = "API Error";

      queryClient.ensureQueryData({
        queryKey: ["user-top-entity", "artist", "week", props.user?.name],
        queryFn: () => {
          return {
            data: {},
            hasError: true,
            errorMessage,
            loading: false,
          };
        },
      });

      renderWithProviders(
        <UserTopEntity {...props} />,
        {},
        {
          wrapper: reactQueryWrapper,
        }
      );
      await waitFor(() => {
        expect(screen.getByTestId("error-message")).toBeInTheDocument();
      });

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.queryByTestId("listen")).not.toBeInTheDocument();
    });
  });
});
