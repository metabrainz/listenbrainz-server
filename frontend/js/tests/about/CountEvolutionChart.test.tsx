import React from "react";
import { render, screen } from "@testing-library/react";
import { ResponsiveLine } from "@nivo/line";
import CountEvolutionChart, {
  alignMonths,
} from "../../src/about/current-status/CountEvolutionChart";
import { COLOR_LB_BLUE, COLOR_LB_ORANGE } from "../../src/utils/constants";

jest.mock("@nivo/line", () => ({ ResponsiveLine: jest.fn(() => null) }));
jest.mock("../../src/explore/fresh-releases/utils", () => ({
  useMediaQuery: () => false,
}));

const users = [
  { period: "2025-01-01T00:00:00+00:00", total_users: 10, new_users: 10 },
  { period: "2025-03-01T00:00:00+00:00", total_users: 20, new_users: 10 },
];
const listens = [
  { period: "2025-02-01", total_listens: 1000000000, new_listens: 1000000000 },
  { period: "2025-03-01", total_listens: 3000000000, new_listens: 2000000000 },
];

it("shows an empty state before either history is available", () => {
  render(
    <CountEvolutionChart userCountEvolution={[]} listenCountEvolution={[]} />
  );
  expect(screen.getByText("No data available")).toBeInTheDocument();
  expect(ResponsiveLine).not.toHaveBeenCalled();
});

it("aligns months, filling only internal gaps in cumulative data", () => {
  expect(
    alignMonths(
      [
        { period: "2025-02-01", total: 5, newCount: 5 },
        { period: "2025-04-01", total: 8, newCount: 3 },
      ],
      ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05"]
    )
  ).toEqual([
    null,
    { total: 5, newCount: 5 },
    { total: 5, newCount: 0 },
    { total: 8, newCount: 3 },
    null,
  ]);
});

it("plots both histories on independent scales and matches each axis to its line color", () => {
  render(
    <CountEvolutionChart
      userCountEvolution={users}
      listenCountEvolution={listens}
    />
  );
  const props = (ResponsiveLine as jest.Mock).mock.calls[0][0];
  expect(props.colors).toEqual([COLOR_LB_ORANGE, COLOR_LB_BLUE]);
  expect(props.data[0].data).toMatchObject([
    { x: "2025-01", y: 0.5 },
    { x: "2025-02", y: 0.5 },
    { x: "2025-03", y: 1 },
  ]);
  expect(props.data[1].data).toMatchObject([
    { x: "2025-01", y: null },
    { x: "2025-02", y: 1 / 3 },
    { x: "2025-03", y: 1 },
  ]);
  const axes = props.layers.find(
    (layer: unknown) => typeof layer === "function"
  );
  render(<svg>{axes({ innerWidth: 600, innerHeight: 300 })}</svg>);
  const left = screen.getByTestId("axis-left");
  const right = screen.getByTestId("axis-right");
  expect(left).toHaveAttribute("fill", COLOR_LB_ORANGE);
  expect(right).toHaveAttribute("fill", COLOR_LB_BLUE);
  expect(screen.getByTestId("axis-line-left")).toHaveAttribute(
    "stroke",
    COLOR_LB_ORANGE
  );
  expect(screen.getByTestId("axis-line-right")).toHaveAttribute(
    "stroke",
    COLOR_LB_BLUE
  );
  expect(left).toHaveTextContent("20");
  expect(right).toHaveTextContent("3B");
});

it("shows compact counts for both histories in a shared monthly tooltip", () => {
  render(
    <CountEvolutionChart
      userCountEvolution={users}
      listenCountEvolution={listens}
    />
  );
  const props = (ResponsiveLine as jest.Mock).mock.calls[0][0];
  render(
    props.sliceTooltip({
      slice: {
        points: props.data.map(
          (s: { id: string; data: unknown[] }, i: number) => ({
            serieId: s.id,
            serieColor: props.colors[i],
            data: s.data[2],
          })
        ),
      },
    })
  );
  expect(screen.getByText("20")).toBeInTheDocument();
  expect(screen.getByText("3B")).toBeInTheDocument();
  expect(screen.getByText("New users: 10")).toBeInTheDocument();
  expect(screen.getByText("Listens submitted: 2B")).toBeInTheDocument();
});

it("keeps the user graph usable when listen history is unavailable", () => {
  render(
    <CountEvolutionChart userCountEvolution={users} listenCountEvolution={[]} />
  );
  const props = (ResponsiveLine as jest.Mock).mock.calls[0][0];
  expect(props.data[0].data[2].y).toBe(1);
  expect(
    props.data[1].data.every((point: { y: number | null }) => point.y === null)
  ).toBe(true);
  expect(screen.getByText(/no data available/)).toBeInTheDocument();
});
