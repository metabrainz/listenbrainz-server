import * as React from "react";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Navbar from "../../src/components/Navbar";
import { setTheme, themeStorageKey } from "../../src/utils/theme";
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

  it("switches the theme and keeps its accessible state in sync", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Navbar />);

    const toggle = screen.getByRole("button", {
      name: "Switch to dark mode",
    });
    expect(toggle).toHaveAttribute("data-theme-toggle");
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    await user.click(toggle);

    expect(document.documentElement.dataset.bsTheme).toBe("dark");
    expect(window.localStorage.getItem(themeStorageKey)).toBe("dark");
    expect(
      screen.getByRole("button", { name: "Switch to light mode" })
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("updates when the legacy navigation changes the theme", () => {
    renderWithProviders(<Navbar />);

    act(() => setTheme("dark"));

    expect(
      screen.getByRole("button", { name: "Switch to light mode" })
    ).toHaveAttribute("aria-pressed", "true");
  });
});
