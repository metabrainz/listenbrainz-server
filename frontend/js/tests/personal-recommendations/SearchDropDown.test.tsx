import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchDropDown, {
  SearchDropDownProps,
} from "../../src/personal-recommendations/SearchDropDown";

const mockAction = jest.fn();
const props: SearchDropDownProps = {
  action: mockAction,
  suggestions: ["hrik2001", "riksucks"],
};

describe("SearchDropDown", () => {
  it("renders a list of suggestions as buttons", () => {
    render(<SearchDropDown {...props} />);

    const suggestionButtons = screen.getAllByRole("menuitem");
    expect(suggestionButtons).toHaveLength(2);
    expect(suggestionButtons.at(0)).toHaveTextContent("hrik2001");
    expect(suggestionButtons.at(1)).toHaveTextContent("riksucks");
  });

  it("calls the action with the correct name when a suggestion is clicked", async () => {
    const user = userEvent.setup();
    render(<SearchDropDown {...props} />);

    const firstSuggestion = screen.getByRole("menuitem", {
      name: /hrik2001/i,
    });
    await user.click(firstSuggestion);

    expect(mockAction).toHaveBeenCalledTimes(1);
    expect(mockAction).toHaveBeenCalledWith("hrik2001");
  });

  it("renders nothing if suggestions are not provided", () => {
    render(<SearchDropDown action={mockAction} suggestions={[]} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
