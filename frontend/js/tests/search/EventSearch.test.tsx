import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import EventSearch from "../../src/search/EventSearch";
import APIService from "../../src/utils/APIService";
import * as utils from "../../src/utils/utils";
import { ReactQueryWrapper } from "../test-react-query";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

const searchResults = {
  count: 42,
  offset: 0,
  events: [
    {
      id: "3a65af9a-3a3b-4df9-adfb-05e8be443c15",
      name: "Glastonbury Festival 2026",
      score: 100,
      type: "Festival",
      "life-span": { begin: "2026-06-24" },
      relations: [
        {
          type: "main performer",
          "type-id": "936c7c95-3156-3889-a062-8a0cd57f8946",
          direction: "backward",
          artist: {
            id: "a74b1b7f-71a5-4011-9441-d0b5e4122711",
            name: "Radiohead",
            "sort-name": "Radiohead",
          },
        },
        {
          type: "held at",
          "type-id": "e2c6f697-07dc-38b1-be0b-83d740165532",
          direction: "forward",
          place: {
            id: "4d43b0d4-5f4a-4b2e-9f0e-1d2c3b4a5e6f",
            name: "Worthy Farm",
          },
        },
        {
          type: "held in",
          "type-id": "542f8484-8bc7-3ce5-a022-747850b2b928",
          direction: "forward",
          area: {
            id: "6b7c8d9e-0f1a-2b3c-4d5e-6f7a8b9c0d1e",
            name: "Somerset",
          },
        },
      ],
    },
    {
      id: "7f3d1c2b-8e9a-4b5c-9d0e-1f2a3b4c5d6e",
      name: "Reading Festival 2026",
      score: 90,
      relations: [
        {
          type: "held in",
          "type-id": "542f8484-8bc7-3ce5-a022-747850b2b928",
          direction: "forward",
          area: {
            id: "8a4b2c1d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
            name: "Reading",
          },
        },
      ],
    },
  ],
};

const renderEventSearch = (
  eventLookup: jest.Mock,
  initialEntry = "/search/?search_term=festival&search_type=event"
) => {
  const apiService = new APIService("foo");
  apiService.eventLookup = eventLookup;
  return renderWithProviders(
    <MemoryRouter initialEntries={[initialEntry]}>
      <EventSearch searchQuery="festival" />
    </MemoryRouter>,
    { APIService: apiService },
    { wrapper: ReactQueryWrapper },
    false
  );
};

describe("<EventSearch />", () => {
  beforeEach(() => {
    jest.spyOn(utils, "getEventArtFromEventMBID").mockResolvedValue(undefined);
  });

  it("looks up the search term and renders a card per event", async () => {
    const eventLookup = jest.fn().mockResolvedValue(searchResults);
    renderEventSearch(eventLookup);

    await waitFor(() => {
      expect(eventLookup).toHaveBeenCalledWith("festival", 0, 30);
    });

    expect(
      await screen.findByRole("link", { name: "Glastonbury Festival 2026" })
    ).toHaveAttribute("href", "/event/3a65af9a-3a3b-4df9-adfb-05e8be443c15/");
    expect(
      screen.getByRole("link", { name: "Reading Festival 2026" })
    ).toHaveAttribute("href", "/event/7f3d1c2b-8e9a-4b5c-9d0e-1f2a3b4c5d6e/");
  });

  it("pulls the performers and the venue out of the MusicBrainz relations", async () => {
    const eventLookup = jest.fn().mockResolvedValue(searchResults);
    renderEventSearch(eventLookup);

    expect(
      await screen.findByRole("link", { name: "Radiohead" })
    ).toHaveAttribute("href", "/artist/a74b1b7f-71a5-4011-9441-d0b5e4122711/");
    expect(screen.getByTitle("Worthy Farm, Somerset")).toBeInTheDocument();
    // the second event has no "held at", only a "held in" area
    expect(screen.getByTitle("Reading")).toBeInTheDocument();
  });

  it("offsets the lookup by the page number in the URL", async () => {
    const eventLookup = jest.fn().mockResolvedValue(searchResults);
    renderEventSearch(
      eventLookup,
      "/search/?search_term=festival&search_type=event&page=3"
    );

    await waitFor(() => {
      expect(eventLookup).toHaveBeenCalledWith("festival", 60, 30);
    });
  });

  it("shows an error message when the lookup fails", async () => {
    const eventLookup = jest
      .fn()
      .mockRejectedValue(new Error("Could not reach MusicBrainz"));
    renderEventSearch(eventLookup);

    const alert = await screen.findByText("Could not reach MusicBrainz");
    expect(alert).toHaveClass("alert-danger");
  });
});
