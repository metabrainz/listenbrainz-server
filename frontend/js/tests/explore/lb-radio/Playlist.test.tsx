import * as React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import { ReactQueryWrapper } from "../../test-react-query";
import { Playlist } from "../../../src/explore/lb-radio/components/Playlist";

const renderPlaylist = (element: React.ReactElement) =>
  renderWithProviders(<ReactQueryWrapper>{element}</ReactQueryWrapper>);

const makeTrack = (id: string, title: string): JSPFTrack => ({
  id,
  identifier: [`https://musicbrainz.org/recording/${id}`],
  title,
  creator: "Moondog",
});

const playlist: JSPFPlaylist = {
  title: "LB Radio for artist Moondog",
  annotation: "",
  creator: "listenbrainz",
  identifier: "",
  date: "",
  track: [
    makeTrack("aaaaaaaa-0000-0000-0000-000000000001", "Bird's Lament"),
    makeTrack("aaaaaaaa-0000-0000-0000-000000000002", "Stamping Ground"),
  ],
};

describe("LB Radio Playlist", () => {
  it("removes the right track through its card menu", async () => {
    const onRemoveTrack = jest.fn();
    renderPlaylist(
      <Playlist
        playlist={playlist}
        onRemoveTrack={onRemoveTrack}
        onReorderTracks={jest.fn()}
      />
    );

    // One "Remove from playlist" item per track card, in playlist order
    const removeButtons = screen.getAllByRole("menuitem", {
      name: "Remove from playlist",
    });
    expect(removeButtons).toHaveLength(2);
    await userEvent.click(removeButtons[1]);

    expect(onRemoveTrack).toHaveBeenCalledTimes(1);
    expect(onRemoveTrack).toHaveBeenCalledWith(playlist.track[1]);
  });

  it("does not offer removal when no handler is passed", () => {
    renderPlaylist(<Playlist playlist={playlist} />);
    expect(
      screen.queryAllByRole("menuitem", { name: "Remove from playlist" })
    ).toHaveLength(0);
  });

  it("shows drag handles so tracks can be reordered", () => {
    const { container } = renderPlaylist(
      <Playlist
        playlist={playlist}
        onRemoveTrack={jest.fn()}
        onReorderTracks={jest.fn()}
      />
    );
    // The drag handle icon is aria-hidden, so there is no accessible query for it
    // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
    expect(container.querySelectorAll(".drag-handle")).toHaveLength(2);
  });

  it("is read-only when no handlers are passed", () => {
    const { container } = renderPlaylist(<Playlist playlist={playlist} />);
    // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
    expect(container.querySelectorAll(".drag-handle")).toHaveLength(0);
  });
});
