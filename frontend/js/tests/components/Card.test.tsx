import * as React from "react";
import Card from "../../src/components/Card";
import { render, screen } from "@testing-library/react";

describe("Card", () => {
  it("renders correctly", () => {
    render(<Card>Test</Card>);
    expect(screen.getByText(/Test/)).toBeInTheDocument();
  });
});
