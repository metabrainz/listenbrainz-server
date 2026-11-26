import * as React from "react";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Navbar from "../../src/components/Navbar";
import { setThemePreference, themeStorageKey } from "../../src/utils/theme";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

jest.mock("../../src/common/Username", () => {
  function MockUsername() {
    return <div />;
  }

  return MockUsername;
});

describe("Navbar theme toggle", () => {
  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
  });

  it("starts new visitors on Auto and cycles Auto -> Light -> Dark", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Navbar />);

    const toggle = screen.getByRole("button", {
      name: "Theme: Auto. Click to switch to Light mode",
    });
    expect(toggle).toHaveAttribute("data-theme-toggle");
    expect(toggle).toHaveAttribute("title", "Click to switch to Light mode");

    await user.click(toggle);
    expect(window.localStorage.getItem(themeStorageKey)).toBe("light");
    expect(toggle).toHaveAccessibleName(
      "Theme: Light. Click to switch to Dark mode"
    );

    await user.click(toggle);
    expect(document.documentElement.dataset.bsTheme).toBe("dark");
    expect(window.localStorage.getItem(themeStorageKey)).toBe("dark");
    expect(toggle).toHaveAccessibleName(
      "Theme: Dark. Click to switch to Auto mode"
    );

    await user.click(toggle);
    expect(window.localStorage.getItem(themeStorageKey)).toBe("system");
    expect(toggle).toHaveAccessibleName(
      "Theme: Auto. Click to switch to Light mode"
    );
  });

  it("updates when the theme is changed elsewhere", () => {
    renderWithProviders(<Navbar />);

    act(() => setThemePreference("dark"));

    expect(
      screen.getByRole("button", {
        name: "Theme: Dark. Click to switch to Auto mode",
      })
    ).toBeInTheDocument();
  });
});
