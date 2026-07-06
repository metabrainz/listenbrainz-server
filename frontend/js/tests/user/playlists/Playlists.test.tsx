import React, { ComponentProps } from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UserPlaylists, {
  SortOption,
} from "../../../src/user/playlists/Playlists";
import { PlaylistType } from "../../../src/playlists/utils";
import PlaylistView from "../../../src/user/playlists/playlistView.d";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import userPlaylistsMock from "../../__mocks__/userPlaylistsProps.json";

type UserPlaylistsComponentProps = ComponentProps<typeof UserPlaylists>;

jest.unmock("react-toastify");

const user = userEvent.setup();
const USER_NAME = "Coder";

const { loaderPlaylists, searchResults } = userPlaylistsMock;

const mockFn = jest.fn;

const createProps = (
  overrides: Partial<UserPlaylistsComponentProps> = {}
): UserPlaylistsComponentProps => ({
  playlists: loaderPlaylists as JSPFObject[],
  user: { id: 1, name: USER_NAME },
  playlistCount: loaderPlaylists.length,
  pageCount: 1,
  page: 1,
  playlistType: PlaylistType.playlists,
  searchQuery: "",
  urlSort: SortOption.RELEVANCE,
  isLoading: false,
  handleClickPrevious: mockFn(),
  handleClickNext: mockFn(),
  handleSetPlaylistType: mockFn(),
  onSearchSubmit: mockFn(),
  onSortChangeDuringSearch: mockFn(),
  initialView: PlaylistView.GRID,
  setPersistentView: mockFn(),
  initialSort: SortOption.DATE_CREATED,
  setPersistentSort: mockFn(),
  ...overrides,
});

const renderPlaylists = (overrides: Partial<UserPlaylistsComponentProps> = {}) => {
  const props = createProps(overrides);
  renderWithProviders(
    <UserPlaylists {...props} />,
    {
      currentUser: {
        id: 1,
        name: USER_NAME,
        auth_token: "token",
      },
    },
    {},
    true
  );
  return props;
};

const getSearchInput = () =>
  screen.getByPlaceholderText("Search playlists") as HTMLInputElement;

const submitSearch = async () => {
  await user.click(
    screen.getByRole("button", {
      name: /search playlists/i,
    })
  );
};

describe("UserPlaylists search", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls onSearchSubmit with the trimmed query on valid submit", async () => {
    const onSearchSubmit = jest.fn();
    renderPlaylists({ onSearchSubmit });

    await user.type(getSearchInput(), "  test  ");
    await submitSearch();

    expect(onSearchSubmit).toHaveBeenCalledWith("test");
  });

  it("calls onSearchSubmit with a short query so the wrapper can clear search params", async () => {
    const onSearchSubmit = jest.fn();
    renderPlaylists({ onSearchSubmit });

    await user.type(getSearchInput(), "ab");
    await submitSearch();

    expect(onSearchSubmit).toHaveBeenCalledWith("ab");
  });

  it("shows browse empty message when there are no playlists", () => {
    renderPlaylists({ playlists: [], playlistCount: 0 });

    expect(
      screen.getByText("No playlists to show yet. Come back later !")
    ).toBeInTheDocument();
  });

  it("shows search empty message when search is active and there are no results", () => {
    renderPlaylists({
      playlists: [],
      playlistCount: 0,
      searchQuery: "missing",
    });

    expect(
      screen.getByText('No playlists match "missing"')
    ).toBeInTheDocument();
  });

  it("calls onSearchSubmit with an empty string when the input is cleared during search", async () => {
    const onSearchSubmit = jest.fn();
    renderPlaylists({
      onSearchSubmit,
      searchQuery: "test",
      playlists: searchResults as JSPFObject[],
    });

    await user.clear(getSearchInput());

    expect(onSearchSubmit).toHaveBeenCalledWith("");
  });

  it("shows a loading message while loader navigation is in progress", () => {
    renderPlaylists({ isLoading: true, searchQuery: "test" });

    expect(screen.getByText("Loading search results...")).toBeInTheDocument();
    expect(screen.queryByText("Alpha Playlist")).not.toBeInTheDocument();
  });

  it("shows browse loading message when not searching", () => {
    renderPlaylists({ isLoading: true });

    expect(screen.getByText("Loading playlists...")).toBeInTheDocument();
  });

  it("calls onSortChangeDuringSearch when sort changes during an active search", async () => {
    const onSortChangeDuringSearch = jest.fn();
    renderPlaylists({
      onSortChangeDuringSearch,
      searchQuery: "test",
      playlists: searchResults as JSPFObject[],
    });

    await user.selectOptions(screen.getByLabelText("Sort by:"), SortOption.TITLE);

    expect(onSortChangeDuringSearch).toHaveBeenCalledWith(SortOption.TITLE);
  });
});
