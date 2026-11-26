import * as React from "react";
import { act, render, screen } from "@testing-library/react";

import NoFreshnessImage from "../../src/components/NoFreshnessImage";
import { setTheme } from "../../src/utils/theme";

describe("NoFreshnessImage", () => {
  beforeEach(() => {
    document.documentElement.dataset.bsTheme = "light";
    document.documentElement.style.colorScheme = "light";
    window.localStorage.clear();
  });

  it("uses the matching artwork and updates when the theme changes", () => {
    render(<NoFreshnessImage alt="No recommendations to show" />);

    const image = screen.getByRole("img", {
      name: "No recommendations to show",
    });
    expect(image).toHaveAttribute(
      "src",
      "/static/img/recommendations/no-freshness.png"
    );

    act(() => setTheme("dark"));

    expect(image).toHaveAttribute(
      "src",
      "/static/img/recommendations/no-freshness-dark.png"
    );
  });
});
