import * as React from "react";
import { screen } from "@testing-library/react";
import EventCard from "../../../src/explore/events/components/EventCard";
import * as utils from "../../../src/utils/utils";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const props = {
  eventMBID: "3a65af9a-3a3b-4df9-adfb-05e8be443c15",
  eventName: "Glastonbury Festival 2026",
  eventType: "Festival",
  eventDate: "2026-12-01",
  performers: [
    { id: "8a0a4f0f-0e0e-4d0e-9e0e-0e0e0e0e0e0e", name: "Radiohead" },
    { id: "9b1b5f1f-1f1f-4e1f-8f1f-1f1f1f1f1f1f", name: "Portishead" },
  ],
  placeName: "Worthy Farm",
  areaName: "Pilton",
  showEventTitle: true,
  showArtist: true,
  showInformation: true,
  dateFormatOptions: { year: "numeric", month: "short" } as const,
};

describe("<EventCard />", () => {
  let getEventArtSpy: jest.SpyInstance;

  beforeEach(() => {
    getEventArtSpy = jest
      .spyOn(utils, "getEventArtFromEventMBID")
      .mockResolvedValue(undefined);
  });

  it("renders the event name as a link to the event page", () => {
    renderWithProviders(<EventCard {...props} />);
    expect(
      screen.getByRole("link", { name: "Glastonbury Festival 2026" })
    ).toHaveAttribute("href", "/event/3a65af9a-3a3b-4df9-adfb-05e8be443c15/");
  });

  it("renders each performer as a link to their artist page", () => {
    renderWithProviders(<EventCard {...props} />);
    expect(screen.getByRole("link", { name: "Radiohead" })).toHaveAttribute(
      "href",
      "/artist/8a0a4f0f-0e0e-4d0e-9e0e-0e0e0e0e0e0e/"
    );
    expect(screen.getByRole("link", { name: "Portishead" })).toHaveAttribute(
      "href",
      "/artist/9b1b5f1f-1f1f-4e1f-8f1f-1f1f1f1f1f1f/"
    );
  });

  it("shows the venue and the area on their own line", () => {
    renderWithProviders(<EventCard {...props} />);
    expect(screen.getByTitle("Worthy Farm, Pilton")).toBeInTheDocument();
  });

  it("falls back to the area name when the event has no place", () => {
    renderWithProviders(<EventCard {...props} placeName={undefined} />);
    expect(screen.getByTitle("Pilton")).toBeInTheDocument();
  });

  it("shows the event type", () => {
    renderWithProviders(<EventCard {...props} />);
    expect(screen.getByText("Festival")).toBeInTheDocument();
  });

  it("defaults the event type to Event when MusicBrainz has none", () => {
    renderWithProviders(<EventCard {...props} eventType={null} />);
    expect(screen.getByText("Event")).toBeInTheDocument();
  });

  it("renders the event art once the Event Art Archive resolves", async () => {
    getEventArtSpy.mockResolvedValue("https://example.org/event-art.jpg");
    renderWithProviders(<EventCard {...props} />);

    const image = await screen.findByAltText(
      "Glastonbury Festival 2026 - Radiohead, Portishead - Worthy Farm, Pilton"
    );
    expect(image).toHaveAttribute("src", "https://example.org/event-art.jpg");
  });

  it("shows a placeholder when the event has no art", () => {
    renderWithProviders(<EventCard {...props} />);
    expect(getEventArtSpy).toHaveBeenCalledWith(props.eventMBID);
    expect(
      screen.queryByAltText(/Glastonbury Festival 2026/)
    ).not.toBeInTheDocument();
  });
});
