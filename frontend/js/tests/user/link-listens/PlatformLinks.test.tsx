import * as React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import PlatformLinks from "../../../src/settings/link-listens/PlatformLinks";
import { getMissingDataLinks } from "../../../src/settings/link-listens/utils";

const row: UnlinkedListens = {
  artist_name: "Example artist",
  recording_name: "Example song",
  release_name: "Example album",
  listened_at: "2026-11-04T10:00:00.000Z",
  recording_msid: "c0f95f14-f222-4a1d-9068-9b092716ef94",
  additional_info: {
    spotify_id: "2TZIQDtf2H4bazKfBa6I4T",
    spotify_album_id: "2HaqZjwdtGVdDsoenjoJrT",
  },
};
const links = getMissingDataLinks(row);
const user = userEvent.setup();

function Card({ id = "first", items = links }) {
  return (
    <div className="listen-card" data-testid={id}>
      <button type="button" data-bs-toggle="dropdown">
        More actions
      </button>
      <ul className="dropdown-menu">
        <PlatformLinks links={items} />
      </ul>
    </div>
  );
}

function renderCard(items = links) {
  return render(
    <MemoryRouter>
      <Card items={items} />
    </MemoryRouter>
  );
}

describe("PlatformLinks", () => {
  it("starts collapsed and preserves full accessible labels on compact actions", async () => {
    renderCard();
    expect(
      screen.getByRole("link", { name: "Open in Spotify" })
    ).not.toBeVisible();
    const summary = screen.getByText("Spotify", { selector: "summary" });
    await user.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    expect(
      screen.getAllByRole("link").map((link) => link.textContent?.trim())
    ).toEqual([
      "Open in Spotify",
      "Open album",
      "Look up album in\nHarmony",
      "Look up album in SAMBL",
    ]);
    links.forEach((item) => {
      const anchor = screen.getByRole("link", { name: item.label });
      expect(anchor).toHaveAttribute("href", item.href);
      expect(anchor).toHaveAttribute("title", item.label);
      expect(anchor).toHaveAttribute("target", "_blank");
      expect(anchor).toHaveAttribute("rel", "noopener noreferrer");
    });
    await user.click(summary);
    expect(
      screen.getByRole("link", { name: "Open in Spotify" })
    ).not.toBeVisible();
  });

  it("stops only expansion clicks from reaching the outer menu listener", async () => {
    renderCard();
    const click = jest.fn();
    document.addEventListener("click", click);
    try {
      await user.click(screen.getByText("Spotify", { selector: "summary" }));
      expect(click).not.toHaveBeenCalled();
      fireEvent.click(screen.getByRole("link", { name: "Open in Spotify" }));
      expect(click).toHaveBeenCalledTimes(1);
    } finally {
      document.removeEventListener("click", click);
    }
  });

  it("collapses only its owning card when that dropdown closes", async () => {
    render(
      <MemoryRouter>
        <Card />
        <Card id="second" />
      </MemoryRouter>
    );
    const first = within(screen.getByTestId("first"));
    const second = within(screen.getByTestId("second"));
    await user.click(first.getByText("Spotify", { selector: "summary" }));
    await user.click(second.getByText("Spotify", { selector: "summary" }));
    fireEvent(
      first.getByRole("button", { name: "More actions" }),
      new Event("hidden.bs.dropdown")
    );
    expect(
      first.getByText("Spotify", { selector: "summary" }).closest("details")
    ).not.toHaveAttribute("open");
    expect(
      first.getByRole("link", { name: "Open in Spotify" })
    ).not.toBeVisible();
    expect(
      second.getByRole("link", { name: "Open in Spotify" })
    ).toBeInTheDocument();
  });

  it("updates the existing dropdown position when a platform expands", async () => {
    const update = jest.fn();
    const getInstance = jest.fn(() => ({ update }));
    const bootstrap = { Dropdown: { getInstance } };
    const previous = Object.getOwnPropertyDescriptor(window, "bootstrap");
    Object.defineProperty(window, "bootstrap", {
      value: bootstrap,
      configurable: true,
    });
    try {
      renderCard();
      const summary = screen.getByText("Spotify", { selector: "summary" });
      await user.click(summary);
      fireEvent(summary.parentElement!, new Event("toggle"));
      expect(getInstance).toHaveBeenCalledWith(
        screen.getByRole("button", { name: "More actions" })
      );
      expect(update).toHaveBeenCalled();
    } finally {
      if (previous) Object.defineProperty(window, "bootstrap", previous);
      else Reflect.deleteProperty(window, "bootstrap");
    }
  });

  it("cleans up the owning dropdown listener on unmount", () => {
    const { unmount } = renderCard();
    const toggle = screen.getByRole("button", { name: "More actions" });
    const remove = jest.spyOn(toggle, "removeEventListener");
    unmount();
    expect(remove).toHaveBeenCalledWith(
      "hidden.bs.dropdown",
      expect.any(Function)
    );
  });

  it("keeps a single-action platform grouped and source-only searches explicit", async () => {
    renderCard(
      getMissingDataLinks({
        ...row,
        additional_info: { music_service_name: "Bandcamp" },
      })
    );
    await user.click(screen.getByText("Bandcamp", { selector: "summary" }));
    expect(
      screen.getByRole("link", { name: "Search Bandcamp for album" })
    ).toHaveTextContent("Search for album");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("keeps platform order and expands groups independently", async () => {
    renderCard(
      getMissingDataLinks({
        ...row,
        additional_info: { ...row.additional_info, youtube_id: "dQw4w9WgXcQ" },
      })
    );
    expect(
      screen
        .getAllByText(/Spotify|YouTube/, { selector: "summary" })
        .map((summary) => summary.textContent?.trim())
    ).toEqual(["Spotify", "YouTube"]);
    await user.click(screen.getByText("Spotify", { selector: "summary" }));
    expect(
      screen.getByRole("link", { name: "Open in YouTube" })
    ).not.toBeVisible();
    await user.click(screen.getByText("YouTube", { selector: "summary" }));
    expect(
      screen.getByRole("link", { name: "Open in YouTube" })
    ).toBeInTheDocument();
  });

  it("does not reinterpret source destinations as tracks", async () => {
    renderCard(
      getMissingDataLinks({
        ...row,
        release_name: null,
        additional_info: {
          origin_url: "https://soundcloud.com/example-artist/sets/example-set",
        },
      })
    );
    await user.click(screen.getByText("SoundCloud", { selector: "summary" }));
    expect(
      screen.getByRole("link", { name: "Open in SoundCloud" })
    ).toHaveTextContent("Open in SoundCloud");
    expect(
      screen.getByRole("link", { name: "Search SoundCloud for track" })
    ).toHaveTextContent("Search for track");
  });

  it("preserves distinct album links within one platform", async () => {
    const items = getMissingDataLinks({
      ...row,
      additional_info: {
        spotify_album_id: "2HaqZjwdtGVdDsoenjoJrT",
        origin_url: "https://open.spotify.com/album/0123456789012345678901",
      },
    });
    renderCard(items);
    await user.click(screen.getByText("Spotify", { selector: "summary" }));
    expect(
      screen.getAllByRole("link").map((anchor) => anchor.getAttribute("href"))
    ).toEqual(items.map((item) => item.href));
  });

  it("renders nothing when no validated links exist", () => {
    const { container } = renderCard([]);
    expect(container.querySelector("details")).toBeNull();
    expect(container.querySelector(".link-listens-service-links")).toBeNull();
  });
});
