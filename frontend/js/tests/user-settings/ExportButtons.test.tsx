import * as React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExportButtons from "../../src/settings/export/ExportButtons";

describe("Export date range", () => {
  let fetchSpy: jest.SpyInstance;

  beforeEach(() => {
    fetchSpy = jest.spyOn(global, "fetch").mockImplementation(async (url) => {
      const data =
        url === "/export/list/"
          ? []
          : {
              export_id: 1,
              type: "export_all_user_data",
              status: "waiting",
              created: "2026-01-01T00:00:00Z",
              progress: "Your data export will start soon.",
            };
      return new Response(JSON.stringify(data), { status: 200 });
    });
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("shows saved local bounds for a completed export after loading the page", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            export_id: 1,
            type: "export_all_user_data",
            status: "completed",
            created: "2026-01-01T00:00:00Z",
            start_time: 1774742400,
            end_time: 1774825199,
          },
        ]),
        { status: 200 }
      )
    );
    render(<ExportButtons />);
    await userEvent.click(await screen.findByText("Details"));
    expect(screen.getByText("Start date")).toBeVisible();
    expect(screen.getByText("Mar 29, 2026, 12:00 AM")).toBeVisible();
    expect(screen.getByText("End date")).toBeVisible();
    expect(screen.getByText("Mar 29, 2026, 11:59 PM")).toBeVisible();
  });

  it.each([
    [null, "Earliest listen"],
    [0, "Jan 1, 1970, 1:00 AM"],
  ])(
    "shows automatic bounds without treating timestamp zero as missing",
    async (start, expected) => {
      fetchSpy.mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              export_id: 1,
              type: "export_all_user_data",
              status: "completed",
              created: "2026-01-01T00:00:00Z",
              start_time: start,
              end_time: null,
            },
          ]),
          { status: 200 }
        )
      );
      render(<ExportButtons />);
      await userEvent.click(await screen.findByText("Details"));
      expect(screen.getByText(expected)).toBeVisible();
      expect(screen.getByText("Latest listen")).toBeVisible();
    }
  );

  it.each([
    ["", "", {}],
    ["2026-03-29", "", { start_time: 1774742400 }],
    ["", "2026-03-29", { end_time: 1774825199 }],
    [
      "2026-03-29",
      "2026-03-29",
      { start_time: 1774742400, end_time: 1774825199 },
    ],
  ])(
    "exports local dates %s through %s with optional inclusive bounds",
    async (start, end, expected) => {
      // npm test runs in Europe/London; March 29 is a 23-hour day in 2026.
      render(<ExportButtons />);
      await waitFor(() =>
        expect(fetchSpy).toHaveBeenCalledWith("/export/list/", {
          method: "GET",
        })
      );
      fireEvent.change(screen.getByLabelText("Start date (optional)"), {
        target: { value: start },
      });
      fireEvent.change(screen.getByLabelText("End date (optional)"), {
        target: { value: end },
      });
      await userEvent.click(
        screen.getByRole("button", { name: "Export listens" })
      );
      await screen.findByRole("heading", { name: "Export in progress" });
      expect(fetchSpy).toHaveBeenCalledWith(
        "/export/",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(expected),
        })
      );
    }
  );

  it("prevents submitting a reversed date range", async () => {
    render(<ExportButtons />);
    fireEvent.change(screen.getByLabelText("Start date (optional)"), {
      target: { value: "2026-04-02" },
    });
    fireEvent.change(screen.getByLabelText("End date (optional)"), {
      target: { value: "2026-04-01" },
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Start date must be on or before end date."
    );
    const button = screen.getByRole("button", { name: "Export listens" });
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
