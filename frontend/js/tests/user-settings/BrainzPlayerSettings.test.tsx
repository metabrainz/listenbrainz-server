import * as React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/rtl-test-utils";
import BrainzPlayerSettings from "../../src/settings/brainzplayer/BrainzPlayerSettings";
import { hasNotificationPermission } from "../../src/notifications/Notifications";
import { createBrainzPlayerSettings } from "../test-utils/BrainzPlayer-test-utils";

jest.mock("../../src/notifications/Notifications", () => ({
  ...jest.requireActual("../../src/notifications/Notifications"),
  hasNotificationPermission: jest.fn(() => Promise.resolve(true)),
}));

describe("BrainzPlayerSettings", () => {
  beforeEach(() => {
    (hasNotificationPermission as jest.Mock).mockClear();
  });

  it("requests notification permission when notifications are turned on", async () => {
    renderWithProviders(<BrainzPlayerSettings />, {
      userPreferences: {
        brainzplayer: createBrainzPlayerSettings({ notificationsEnabled: false }),
      },
    });
    const toggle = screen.getByRole<HTMLInputElement>("checkbox", {
      name: /show a notification for each track played/i,
    });
    expect(toggle.checked).toBe(false);

    await userEvent.click(toggle);

    expect(toggle.checked).toBe(true);
    expect(hasNotificationPermission).toHaveBeenCalledTimes(1);
  });

  it("does not request permission when notifications are turned off", async () => {
    renderWithProviders(<BrainzPlayerSettings />, {
      userPreferences: {
        brainzplayer: createBrainzPlayerSettings({ notificationsEnabled: true }),
      },
    });
    const toggle = screen.getByRole<HTMLInputElement>("checkbox", {
      name: /show a notification for each track played/i,
    });
    expect(toggle.checked).toBe(true);

    await userEvent.click(toggle);

    expect(toggle.checked).toBe(false);
    expect(hasNotificationPermission).not.toHaveBeenCalled();
  });
});
