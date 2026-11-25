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

describe("Navbar theme menu", () => {
  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
  });

  it("offers Light, Dark and System, and applies the chosen one", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Navbar />);

    const toggle = screen.getByRole("button", { name: "Theme: System" });
    expect(toggle).toHaveAttribute("data-theme-toggle");

    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Light" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "System" })).toHaveAttribute(
      "aria-current",
      "true"
    );

    await user.click(screen.getByRole("button", { name: "Dark" }));

    expect(document.documentElement.dataset.bsTheme).toBe("dark");
    expect(window.localStorage.getItem(themeStorageKey)).toBe("dark");
    expect(
      screen.getByRole("button", { name: "Theme: Dark" })
    ).toBeInTheDocument();
  });

  it("updates when the theme is changed elsewhere", () => {
    renderWithProviders(<Navbar />);

    act(() => setThemePreference("light"));

    expect(
      screen.getByRole("button", { name: "Theme: Light" })
    ).toBeInTheDocument();
  });
});
