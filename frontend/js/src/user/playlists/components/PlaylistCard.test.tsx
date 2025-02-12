import React from "react";
import { render, fireEvent, waitFor, screen } from "@testing-library/react";
import { MemoryRouter as Router } from "react-router-dom";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import PlaylistCard from "./PlaylistCard";
import { render, waitFor, screen } from "@testing-library/react";
import * as PlaylistUtils from "../../../playlists/utils";
import { render, fireEvent } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import PlaylistMenu from "../../../playlists/components/PlaylistMenu";
import * as React from "react";

// Mock PlaylistMenu to render a dummy element so we can detect it in the DOM.
jest.mock("../../../playlists/components/PlaylistMenu", () => () => (
  <div data-testid="playlist-menu">Mock PlaylistMenu</div>
));
/**
 * This test verifies that when the "copy playlist" action is triggered
 * by a user who is not logged in (i.e. missing auth token), an error toast
 * is displayed with a message indicating that the user must be logged in.
 */
test("should show error toast when copying playlist without authentication (list view)", async () => {
  // Create dummy APIService with required function mocks.
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  // Create a dummy playlist object.
  const dummyPlaylist = {
    id: "123", // This will be picked up as the playlist id (assuming getPlaylistId uses this field)
    title: "Test Playlist",
    date: new Date("2023-01-01T00:00:00Z").toISOString(),
    track: [],
    annotation: "<p>Test annotation</p>",
  };
  // Create dummy callbacks.
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  // Provide GlobalAppContext with no auth token.
  const FakeGlobalAppContext = React.createContext({
    APIService: fakeAPIService,
    currentUser: {}, // missing auth_token
  });
  // Because PlaylistCard consumes GlobalAppContext from the "../../../utils/GlobalAppContext",
  // we create a Wrapper that provides our fake context.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <FakeGlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: {}, // User is not logged in
      }}
    >
      {children}
    </FakeGlobalAppContext.Provider>
  );
  // Spy on toast.error to assert it is called.
  const toastErrorSpy = jest.spyOn(toast, "error").mockImplementation(() => {});
  // Render the component in List view, with showOptions false so that the "Save" (copy) action is shown.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" }; // Dummy view enum
  // We need to wrap the component in our provider and Router for routing.
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.LIST}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={false}
        />
      </Router>
    </ProviderWrapper>
  );
  // Find the copy link. In List view without options, the copy button exists as an anchor with "Save" text.
  const copyLink = screen.getByText(/Save/i);
  expect(copyLink).toBeInTheDocument();
  // Click the copy action.
  fireEvent.click(copyLink);
  // Wait for side effects from the async onCopyPlaylist. We expect that toast.error will be called with our error about not being logged in.
  await waitFor(() => {
    expect(toastErrorSpy).toHaveBeenCalled();
  });
  // Optionally, check that toast.error was called with a message that contains "logged in" in its message.
  // Since the ToastMsg component is used, we can't easily match text but we can match toastId.
  expect(toastErrorSpy).toHaveBeenCalledWith(
    expect.anything(),
    expect.objectContaining({ toastId: "auth-error" })
  );
  // Clean up the toast spy.
  toastErrorSpy.mockRestore();
});
/**
 * This test verifies that when a logged-in user triggers the copy action in list view,
 * the playlist is successfully duplicated. It asserts that the API is called with the proper
 * arguments, the new playlist is fetched, the onSuccessfulCopy callback is called with the new playlist,
 * and a success toast (with toastId "copy-playlist-success") is displayed.
 */
test("should successfully copy playlist when authenticated (list view)", async () => {
  const fakeAPIService = {
    copyPlaylist: jest.fn().mockResolvedValue("456"),
    getPlaylist: jest.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          playlist: {
            id: "456",
            title: "Copied Playlist",
            date: new Date("2023-01-02T00:00:00Z").toISOString(),
            track: [],
          },
        }),
    }),
    getPlaylistImage: jest.fn(),
  };
  const dummyPlaylist = {
    id: "123",
    title: "Test Playlist",
    date: new Date("2023-01-01T00:00:00Z").toISOString(),
    track: [],
    annotation: "<p>Test annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  // Use the actual GlobalAppContext so that the component consumes our fake context values.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "fake-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Spy on toast.success.
  const toastSuccessSpy = jest.spyOn(toast, "success").mockImplementation(() => {});
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.LIST}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={false}
        />
      </Router>
    </ProviderWrapper>
  );
  // In list view without options, the copy (save) action appears as an anchor with "Save" text.
  const copyLink = screen.getByText(/Save/i);
  expect(copyLink).toBeInTheDocument();
  fireEvent.click(copyLink);
  await waitFor(() => {
    expect(fakeAPIService.copyPlaylist).toHaveBeenCalledWith("fake-token", "123");
  });
  await waitFor(() => {
    expect(fakeAPIService.getPlaylist).toHaveBeenCalledWith("456", "fake-token");
  });
  await waitFor(() => {
    // Ensure that the onSuccessfulCopy callback gets called with the new playlist.
    expect(onSuccessfulCopy).toHaveBeenCalledWith({
      id: "456",
      title: "Copied Playlist",
      date: new Date("2023-01-02T00:00:00Z").toISOString(),
      track: [],
    });
  });
  // Check that toast.success was called with a toastId of "copy-playlist-success"
  expect(toastSuccessSpy).toHaveBeenCalledWith(
    expect.objectContaining({
      props: expect.objectContaining({
        title: "Duplicated playlist",
      }),
    }),
    expect.objectContaining({ toastId: "copy-playlist-success" })
  );
  toastSuccessSpy.mockRestore();
});
/**
 * This test verifies that when the PlaylistCard is rendered in GRID view for an authenticated user,
 * it calls getPlaylistImage with the proper arguments (using custom cover art layout data defined by getPlaylistExtension)
 * and renders the fetched cover art content.
 */
test("should display fetched cover art in GRID view when authenticated", async () => {
  // Override getPlaylistExtension to return custom cover art layout values.
  jest.spyOn(PlaylistUtils, "getPlaylistExtension").mockReturnValue({
    additional_metadata: {
      cover_art: {
        layout: "layout1",
        dimension: "dim1",
      },
    },
  });
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn().mockResolvedValue("<svg>Test Image</svg>"),
  };
  const dummyPlaylist = {
    id: "789",
    title: "Grid Playlist",
    date: new Date("2023-03-01T00:00:00Z").toISOString(),
    track: [{}, {}],
    annotation: "<p>Grid annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  // Define a dummy enum for view types.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // Create Provider wrapper with an authenticated user.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "fake-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Render the component in GRID view.
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.GRID}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={true}
        />
      </Router>
    </ProviderWrapper>
  );
  // Wait for the async useEffect to call getPlaylistImage with the expected parameters.
  await waitFor(() => {
    expect(fakeAPIService.getPlaylistImage).toHaveBeenCalledWith(
      dummyPlaylist.id,
      "fake-token",
      "dim1",
      "layout1"
    );
  });
  // Assert that the cover art div has been rendered with the fetched SVG content.
  const coverArtDiv = container.querySelector(".cover-art");
  expect(coverArtDiv).toBeInTheDocument();
  expect(coverArtDiv?.innerHTML).toContain("<svg>Test Image</svg>");
  // Restore the mocked getPlaylistExtension.
  (PlaylistUtils.getPlaylistExtension as jest.Mock).mockRestore();
});
/**
 * This test verifies that clicking on the playlist card container or pressing the Enter key
 * in list view triggers a navigation to the corresponding playlist page.
 */
test("should navigate to playlist page when card container is clicked or Enter key pressed (list view)", () => {
  // Create a dummy playlist object.
  const dummyPlaylist = {
    id: "999", // This will be used as the playlist ID.
    title: "Navigation Playlist",
    date: new Date("2023-01-01T00:00:00Z").toISOString(),
    track: [],
    annotation: "<p>Navigation test</p>",
  };
  // Create a dummy APIService with the minimal required mocks.
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  // Set up a spy on useNavigate from react-router-dom.
  const mockedUsedNavigate = jest.fn();
  jest
    .spyOn(require("react-router-dom"), "useNavigate")
    .mockReturnValue(mockedUsedNavigate);
  // Wrap the component with GlobalAppContext provider.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "dummy-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Define a dummy enum for PlaylistView.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // Render the component in LIST view.
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.LIST}
          index={0}
          onSuccessfulCopy={jest.fn()}
          onPlaylistEdited={jest.fn()}
          onPlaylistDeleted={jest.fn()}
          showOptions={true}
        />
      </Router>
    </ProviderWrapper>
  );
  // Get the card container element (which has role "presentation").
  const cardContainer = container.querySelector(".playlist-card-container");
  expect(cardContainer).toBeInTheDocument();
  // Simulate a click event on the container.
  fireEvent.click(cardContainer!);
  expect(mockedUsedNavigate).toHaveBeenCalledWith(`/playlist/${dummyPlaylist.id}/`);
  // Reset the spy call count.
  mockedUsedNavigate.mockClear();
  // Simulate a keyDown event with the Enter key on the container.
  fireEvent.keyDown(cardContainer!, { key: "Enter", code: "Enter", charCode: 13 });
  expect(mockedUsedNavigate).toHaveBeenCalledWith(`/playlist/${dummyPlaylist.id}/`);
  // Restore all mocks.
  jest.restoreAllMocks();
});
/**
 * This test verifies that when getPlaylistImage fails in GRID view (e.g.,
 * due to an error fetching the cover art), the PlaylistCard renders the fallback cover art image
 * (i.e., the placeholder image) as defined in the component.
 */
test("should display fallback cover art when getPlaylistImage fails in GRID view", async () => {
  // Create a fake APIService where getPlaylistImage rejects with an error.
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn().mockRejectedValue(new Error("Image fetch failed")),
  };
  // Dummy playlist object.
  const dummyPlaylist = {
    id: "1010",
    title: "Fallback Test Playlist",
    date: new Date("2023-04-01T00:00:00Z").toISOString(),
    track: [{}, {}],
    annotation: "<p>Fallback annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  // Define a dummy enum for PlaylistView.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // ProviderWrapper that uses GlobalAppContext with an authenticated user.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "valid-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Render the component in GRID view.
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.GRID}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={true}
        />
      </Router>
    </ProviderWrapper>
  );
  // Wait for the async useEffect to complete. We expect getPlaylistImage to have been called.
  await waitFor(() => {
    expect(fakeAPIService.getPlaylistImage).toHaveBeenCalledWith(
      dummyPlaylist.id,
      "valid-token",
      undefined,
      undefined
    );
  });
  // Assert that the cover art div is rendered with the fallback image.
  // Since getPlaylistImage failed, playlistImageString remains undefined and the fallback image will be rendered.
  const coverArtDiv = container.querySelector(".cover-art");
  expect(coverArtDiv).toBeInTheDocument();
  expect(coverArtDiv?.innerHTML).toContain("<img src='/static/img/cover-art-placeholder.jpg'>");
});
test("should successfully copy playlist in GRID view using copy button when options are hidden", async () => {
  /**
   * This test verifies that when an authenticated user clicks on the copy button in GRID view
   * (with showOptions set to false), the copyPlaylist API is called, the new playlist is fetched,
   * the onSuccessfulCopy callback is invoked with the new playlist data, and a success toast is displayed.
   */
  const fakeAPIService = {
    copyPlaylist: jest.fn().mockResolvedValue("999"),
    getPlaylist: jest.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          playlist: {
            id: "999",
            title: "Copied Grid Playlist",
            date: new Date("2023-01-03T00:00:00Z").toISOString(),
            track: [],
          },
        }),
    }),
    getPlaylistImage: jest.fn().mockResolvedValue("<svg>Grid Image</svg>"),
  };
  const dummyPlaylist = {
    id: "321",
    title: "Grid Test Playlist",
    date: new Date("2023-01-01T00:00:00Z").toISOString(),
    track: [{}, {}],
    annotation: "<p>Grid annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "grid-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Spy on toast.success for later assertions
  const toastSuccessSpy = jest.spyOn(toast, "success").mockImplementation(() => {});
  // Define a dummy PlaylistView enum
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // Render the component in GRID view with showOptions set to false (should render a copy button)
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.GRID}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={false}
        />
      </Router>
    </ProviderWrapper>
  );
  // In GRID view with showOptions false, the copy action appears as a button
  const copyButton = container.querySelector("button.playlist-card-action-button");
  expect(copyButton).toBeInTheDocument();
  // Click the copy button to trigger onCopyPlaylist
  fireEvent.click(copyButton!);
  // Wait for copyPlaylist API to be called with the correct arguments
  await waitFor(() => {
    expect(fakeAPIService.copyPlaylist).toHaveBeenCalledWith("grid-token", dummyPlaylist.id);
  });
  // Wait for getPlaylist to be called to fetch the duplicated playlist
  await waitFor(() => {
    expect(fakeAPIService.getPlaylist).toHaveBeenCalledWith("999", "grid-token");
  });
  // Ensure that onSuccessfulCopy is invoked with the new playlist data
  await waitFor(() => {
    expect(onSuccessfulCopy).toHaveBeenCalledWith({
      id: "999",
      title: "Copied Grid Playlist",
      date: new Date("2023-01-03T00:00:00Z").toISOString(),
      track: [],
    });
  });
  // Assert that the success toast is called with toastId "copy-playlist-success"
  expect(toastSuccessSpy).toHaveBeenCalledWith(
    expect.objectContaining({
      props: expect.objectContaining({
        title: "Duplicated playlist",
      }),
    }),
    expect.objectContaining({ toastId: "copy-playlist-success" })
  );
  toastSuccessSpy.mockRestore();
});
/**
 * This test verifies that when the PlaylistCard is rendered in LIST view
 * with showOptions true, the PlaylistMenu dropdown is rendered.
 */
test("should render PlaylistMenu dropdown in list view when showOptions is true", () => {
  // Create a dummy playlist object.
  const dummyPlaylist = {
    id: "555",
    title: "Playlist with Options",
    date: new Date("2023-05-01T00:00:00Z").toISOString(),
    track: [{}, {}],
    annotation: "<p>Options annotation</p>",
  };
  // Create a fake APIService with minimal function mocks.
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  // Provider wrapper to supply GlobalAppContext.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{ APIService: fakeAPIService, currentUser: { auth_token: "test-token" } }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Define a dummy enum for view types.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // Render the PlaylistCard in LIST view with showOptions set to true.
  render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist}
          view={PlaylistView.LIST}
          index={1}
          onSuccessfulCopy={jest.fn()}
          onPlaylistEdited={jest.fn()}
          onPlaylistDeleted={jest.fn()}
          showOptions={true}
        />
      </Router>
    </ProviderWrapper>
  );
  // Verify that the mocked PlaylistMenu is rendered.
  const playlistMenu = screen.getByTestId("playlist-menu");
  expect(playlistMenu).toBeInTheDocument();
});
/**
 * This test verifies that if the playlist does not have a valid playlist ID,
 * clicking the copy action displays an error toast indicating that the playlist ID is missing,
 * and prevents any API calls.
 */
test("should show error toast when copying playlist without valid playlist ID", async () => {
  // Mock getPlaylistId to return an empty string to simulate a missing playlist ID.
  const playlistIdSpy = jest.spyOn(PlaylistUtils, "getPlaylistId").mockReturnValue("");
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  // Create a dummy playlist object without a valid id.
  const dummyPlaylist = {
    title: "Playlist without valid id",
    date: new Date("2023-06-01T00:00:00Z").toISOString(),
    track: [],
    annotation: "<p>No ID annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "dummy-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  
  // Spy on toast.error.
  const toastErrorSpy = jest.spyOn(toast, "error").mockImplementation(() => {});
  
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  
  render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.LIST}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={false}
        />
      </Router>
    </ProviderWrapper>
  );
  
  // Find and click the "Save" link in list view.
  const copyLink = screen.getByText(/Save/i);
  fireEvent.click(copyLink);
  
  // Wait and verify that the error toast is shown with the expected toastId.
  await waitFor(() => {
    expect(toastErrorSpy).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ toastId: "copy-playlist-error" })
    );
  });
  
  // Ensure that the copyPlaylist API was not called.
  expect(fakeAPIService.copyPlaylist).not.toHaveBeenCalled();
  
  // Clean up mocks.
  toastErrorSpy.mockRestore();
  playlistIdSpy.mockRestore();
});
/**
 * This test verifies that when the copyPlaylist API call fails in list view,
 * an error toast is displayed with the error message and toastId "copy-playlist-error",
 * and the onSuccessfulCopy callback is not invoked.
 */
test("should show error toast when API copyPlaylist fails in list view", async () => {
  const fakeAPIService = {
    copyPlaylist: jest.fn().mockRejectedValue(new Error("API failure")),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  const dummyPlaylist = {
    id: "200",
    title: "Error Playlist",
    date: new Date("2023-07-01T00:00:00Z").toISOString(),
    track: [],
    annotation: "<p>Error test annotation</p>",
  };
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: { auth_token: "valid-error-token" },
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  // Spy on toast.error
  const toastErrorSpy = jest.spyOn(toast, "error").mockImplementation(() => {});
  // We define a dummy view object for the tests.
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist as any}
          view={PlaylistView.LIST}
          index={2}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={false}
        />
      </Router>
    </ProviderWrapper>
  );
  // Find the "Save" anchor link in list view.
  const copyLink = screen.getByText(/Save/i);
  fireEvent.click(copyLink);
  await waitFor(() => {
    expect(fakeAPIService.copyPlaylist).toHaveBeenCalledWith("valid-error-token", "200");
  });
  // Wait for the error toast side effect.
  await waitFor(() => {
    expect(toastErrorSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({
          title: "Error",
          message: "API failure"
        }),
      }),
      expect.objectContaining({ toastId: "copy-playlist-error" })
    );
  });
  // Ensure that the onSuccessfulCopy callback is not called since the API failed.
  expect(onSuccessfulCopy).not.toHaveBeenCalled();
  toastErrorSpy.mockRestore();
});
/**
 * This test verifies that when the PlaylistCard is rendered in GRID view while the user is not authenticated,
 * it does not attempt to fetch cover art via getPlaylistImage and instead displays the fallback cover art image.
 */
test("should render fallback cover art in GRID view when not authenticated", async () => {
  // Create a fake APIService where getPlaylistImage is a jest mock function.
  const fakeAPIService = {
    copyPlaylist: jest.fn(),
    getPlaylist: jest.fn(),
    getPlaylistImage: jest.fn(),
  };
  // Define a dummy playlist object.
  const dummyPlaylist = {
    id: "111",
    title: "Grid No Auth Playlist",
    date: new Date("2023-08-01T00:00:00Z").toISOString(),
    track: [{}, {}],
    annotation: "<p>No Auth annotation</p>",
  };
  // Dummy callbacks.
  const onSuccessfulCopy = jest.fn();
  const onPlaylistEdited = jest.fn();
  const onPlaylistDeleted = jest.fn();
  // Create a provider wrapper with no auth token. This should prevent getPlaylistImage from being called.
  const ProviderWrapper = ({ children }: { children: React.ReactNode }) => (
    <GlobalAppContext.Provider
      value={{
        APIService: fakeAPIService,
        currentUser: {}, // Not authenticated
      }}
    >
      {children}
    </GlobalAppContext.Provider>
  );
  const PlaylistView = { LIST: "LIST", GRID: "GRID" };
  // Render the PlaylistCard in GRID view.
  const { container } = render(
    <ProviderWrapper>
      <Router>
        <PlaylistCard
          playlist={dummyPlaylist}
          view={PlaylistView.GRID}
          index={0}
          onSuccessfulCopy={onSuccessfulCopy}
          onPlaylistEdited={onPlaylistEdited}
          onPlaylistDeleted={onPlaylistDeleted}
          showOptions={true}
        />
      </Router>
    </ProviderWrapper>
  );
  // Since user is not authenticated, the useEffect should not call getPlaylistImage.
  await waitFor(() => {
    expect(fakeAPIService.getPlaylistImage).not.toHaveBeenCalled();
  });
  // In absence of a fetched image, the fallback cover art should be rendered.
  const coverArtDiv = container.querySelector(".cover-art");
  expect(coverArtDiv).toBeInTheDocument();
  expect(coverArtDiv?.innerHTML).toContain("cover-art-placeholder.jpg");
});