import * as React from "react";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router";
import RecentDonorsCard from "../../src/recent/components/RecentDonors";
import { ReactQueryWrapper } from "../test-react-query";

const baseDonor: DonationInfoWithPinnedRecording = {
  id: 1,
  donated_at: "",
  donation: 42,
  currency: "eur",
  musicbrainz_id: "Foo",
  is_listenbrainz_user: true,
  listenCount: 1234,
  playlistCount: 12,
  // @ts-ignore: donors without a pinned recording get null from the server
  pinnedRecording: null,
};

const renderCard = (donors: DonationInfoWithPinnedRecording[]) =>
  render(
    <BrowserRouter>
      <ReactQueryWrapper>
        <RecentDonorsCard donors={donors} />
      </ReactQueryWrapper>
    </BrowserRouter>
  );

describe("RecentDonorsCard", () => {
  it("shows a donor's listen and playlist counts with links", () => {
    renderCard([baseDonor]);

    const listens = screen.getByRole("link", { name: /1.2K listens/ });
    expect(listens).toHaveAttribute("href", "/user/Foo/stats/?range=all_time");
    expect(listens).toHaveAttribute("title", "1,234 listens");

    const playlists = screen.getByRole("link", { name: /12 playlists/ });
    expect(playlists).toHaveAttribute("href", "/user/Foo/playlists/");
  });

  it("hides counts that are zero", () => {
    renderCard([{ ...baseDonor, playlistCount: 0 }]);

    expect(screen.getByText(/1.2K listens/)).toBeInTheDocument();
    expect(screen.queryByText(/playlists/)).not.toBeInTheDocument();
  });

  it("shows no stats, and no stray 0, when both counts are zero", () => {
    renderCard([{ ...baseDonor, listenCount: 0, playlistCount: 0 }]);

    expect(screen.queryByText(/listens/)).not.toBeInTheDocument();
    expect(screen.queryByText(/playlists/)).not.toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows no stats for donors who aren't ListenBrainz users", () => {
    renderCard([
      {
        ...baseDonor,
        is_listenbrainz_user: false,
        // @ts-ignore: the server sends null for donors who aren't ListenBrainz users
        listenCount: null,
        // @ts-ignore
        playlistCount: null,
      },
    ]);

    expect(screen.queryByText(/listens/)).not.toBeInTheDocument();
    expect(screen.queryByText(/playlists/)).not.toBeInTheDocument();
  });
});
