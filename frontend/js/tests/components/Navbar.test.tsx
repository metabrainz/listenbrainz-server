import * as React from "react";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "react-toastify";
import Navbar from "../../src/components/Navbar";
import { setThemePreference, themeStorageKey } from "../../src/utils/theme";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

jest.mock("../../src/common/Username", () => {
  function MockUsername() {
    return <div />;
  }

  return MockUsername;
});

jest.mock("react-toastify", () => ({
  toast: Object.assign(jest.fn(), {
    isActive: jest.fn(() => false),
    update: jest.fn(),
  }),
}));

describe("Navbar theme toggle", () => {
  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
    jest.clearAllMocks();
  });

  it("starts new visitors on Light and cycles Light -> Dark -> Auto", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Navbar />);

    const toggle = screen.getByRole("button", {
      name: "Theme: Light. Click to switch to Dark mode",
    });
    expect(toggle).toHaveAttribute("data-theme-toggle");
    expect(toggle).toHaveAttribute("title", "Click to switch to Dark mode");

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

    await user.click(toggle);
    expect(window.localStorage.getItem(themeStorageKey)).toBe("light");
    expect(document.documentElement.dataset.bsTheme).toBe("light");
  });

  it("announces the new mode with a toast, reusing one toast for rapid clicks", async () => {
    const user = userEvent.setup();
    const random = jest.spyOn(Math, "random").mockReturnValue(0.99);
    renderWithProviders(<Navbar />);

    await user.click(
      screen.getByRole("button", { name: /Click to switch to Dark mode/ })
    );
    expect(toast).toHaveBeenCalledTimes(1);
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        props: expect.objectContaining({
          title: "Dark mode",
          // Lines are picked at random; 0.99 selects the last dark line.
          message: "You're welcome.",
        }),
      }),
      expect.objectContaining({ toastId: "theme-change" })
    );

    (toast.isActive as jest.Mock).mockReturnValue(true);
    await user.click(
      screen.getByRole("button", { name: /Click to switch to Auto mode/ })
    );
    expect(toast).toHaveBeenCalledTimes(1);
    expect(toast.update).toHaveBeenCalledWith(
      "theme-change",
      expect.objectContaining({
        render: expect.objectContaining({
          props: expect.objectContaining({ title: "Auto mode" }),
        }),
      })
    );
    random.mockRestore();
  });

  it("does not toast when the theme changes without a click", () => {
    renderWithProviders(<Navbar />);
    act(() => setThemePreference("dark"));
    expect(toast).not.toHaveBeenCalled();
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
