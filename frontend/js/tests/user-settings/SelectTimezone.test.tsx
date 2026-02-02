import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";
import APIServiceClass from "../../src/utils/APIService";
import SelectTimezone from "../../src/settings/select_timezone/SelectTimezone";

const user_timezone = "America/New_York";
const pg_timezones: Array<[string, string]> = [
  ["Africa/Adnodjan", "+3:00:00 GMT"],
  ["America/Adak", "-9:00:00 GMT"],
  ["America/New_York", "-4:00:00 GMT"],
];

const props = {
  pg_timezones,
  user_timezone,
};

jest.unmock("react-toastify");

describe("User settings", () => {
  describe("submitTimezonePage", () => {
    it("renders correctly", async () => {
      render(<SelectTimezone {...props} />);

      await screen.findByRole("heading", { name: /select your timezone/i });
      await screen.findByRole("button", { name: /save timezone/i });
      const defaultOption = await screen.findByRole<HTMLOptionElement>(
        "option",
        { name: "Choose an option" }
      );
      expect(defaultOption.selected).toBe(false);
      expect(defaultOption.disabled).toBe(true);
      expect(
        screen.getByRole<HTMLOptionElement>("option", {
          name: "America/New_York (-4:00:00 GMT)",
        }).selected
      ).toBe(true);
    });
  });

  describe("resetTimezone", () => {
    it("calls API, and sets state + creates a new alert on success", async () => {
      const testAPIService = new APIServiceClass("fnord");
      renderWithProviders(<SelectTimezone {...props} />, {
        APIService: testAPIService,
      });
      // render(<SelectTimezone {...props} />);

      expect(
        screen.getByRole<HTMLOptionElement>("option", {
          name: "America/New_York (-4:00:00 GMT)",
        }).selected
      ).toBe(true);

      await userEvent.selectOptions(
        screen.getByRole("combobox"),
        screen.getByRole("option", { name: "America/Adak (-9:00:00 GMT)" })
      );
      // Check that we correctly set the select option
      expect(
        screen.getByRole<HTMLOptionElement>("option", {
          name: "America/Adak (-9:00:00 GMT)",
        }).selected
      ).toBe(true);
      // It's not a multiselect, ensure the previous option is not selected anymore
      expect(
        screen.getByRole<HTMLOptionElement>("option", {
          name: "America/New_York (-4:00:00 GMT)",
        }).selected
      ).toBe(false);

      const spy = jest
        .spyOn(testAPIService, "resetUserTimezone")
        .mockImplementation(() => Promise.resolve(200));

      // submit the form
      await userEvent.click(screen.getByRole("button"));

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("never_gonna", "America/Adak");
      // expect success message
      screen.getByText(textContentMatcher("Your timezone has been saved."));
    });
  });
});
