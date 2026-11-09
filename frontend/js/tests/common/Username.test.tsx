import * as React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test-utils/rtl-test-utils";
import { ReactQueryWrapper } from "../test-react-query";
import Username from "../../src/common/Username";
import {
  FlairEnum,
  FlairDisplayPreferenceEnum,
} from "../../src/utils/constants";
import FlairsExplanationButton from "../../src/common/flairs/FlairsExplanationButton";

describe("Username component flair display preferences", () => {
  it("renders username with flair class when preference is All", () => {
    renderWithProviders(
      <ReactQueryWrapper>
        <Username username="testuser" selectedFlair={FlairEnum.Wave} />
      </ReactQueryWrapper>,
      { flairDisplayPreference: FlairDisplayPreferenceEnum.All }
    );
    const userElement = screen.getByTitle("testuser");
    expect(userElement.className).toContain("flair wave");
    expect(userElement.className).not.toContain("flair-no-animation");
  });

  it("renders username with flair-no-animation class when preference is NoAnimations", () => {
    renderWithProviders(
      <ReactQueryWrapper>
        <Username username="testuser" selectedFlair={FlairEnum.Wave} />
      </ReactQueryWrapper>,
      { flairDisplayPreference: FlairDisplayPreferenceEnum.NoAnimations }
    );
    const userElement = screen.getByTitle("testuser");
    expect(userElement.className).toContain("flair wave");
    expect(userElement.className).toContain("flair-no-animation");
  });

  it("renders plain username without flair class when preference is Disabled", () => {
    renderWithProviders(
      <ReactQueryWrapper>
        <Username username="testuser" selectedFlair={FlairEnum.Wave} />
      </ReactQueryWrapper>,
      { flairDisplayPreference: FlairDisplayPreferenceEnum.Disabled }
    );
    const userElement = screen.getByTitle("testuser");
    expect(userElement.className).not.toContain("flair");
    expect(userElement.className).not.toContain("wave");
    expect(userElement.textContent).toBe("testuser");
  });

  it("renders flair when ignoreDisplayPreference is true even if preference is Disabled", () => {
    renderWithProviders(
      <ReactQueryWrapper>
        <Username
          username="testuser"
          selectedFlair={FlairEnum.Wave}
          ignoreDisplayPreference
        />
      </ReactQueryWrapper>,
      { flairDisplayPreference: FlairDisplayPreferenceEnum.Disabled }
    );
    const userElement = screen.getByTitle("testuser");
    expect(userElement.className).toContain("flair wave");
    expect(userElement.className).not.toContain("flair-no-animation");
  });
});

describe("FlairsExplanationButton component", () => {
  it("renders explanation button when preference is All", () => {
    renderWithProviders(<FlairsExplanationButton />, {
      flairDisplayPreference: FlairDisplayPreferenceEnum.All,
    });
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("renders explanation button when preference is NoAnimations", () => {
    renderWithProviders(<FlairsExplanationButton />, {
      flairDisplayPreference: FlairDisplayPreferenceEnum.NoAnimations,
    });
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("does not render when preference is Disabled", () => {
    renderWithProviders(<FlairsExplanationButton />, {
      flairDisplayPreference: FlairDisplayPreferenceEnum.Disabled,
    });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

