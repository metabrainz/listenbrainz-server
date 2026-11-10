import * as React from "react";
import { render, screen } from "@testing-library/react";

import EntityCoverArtPlaceholder from "../../src/components/EntityCoverArtPlaceholder";

describe("EntityCoverArtPlaceholder", () => {
  it("renders an accessible placeholder with the transparent logo", () => {
    render(<EntityCoverArtPlaceholder alt="Album art" />);

    expect(screen.getByRole("img", { name: "Album art" })).toHaveClass(
      "cover-art-placeholder"
    );
    expect(screen.getByAltText("")).toHaveAttribute(
      "src",
      "/static/img/listenbrainz_logo_icon.svg"
    );
  });
});
