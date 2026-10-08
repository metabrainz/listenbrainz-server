import { Theme as NivoTheme } from "@nivo/core";
import * as React from "react";
import { useTheme, Theme } from "./theme";

const palette = {
  light: {
    background: "#ffffff",
    text: "#46433a",
    mutedText: "#6b665c",
    border: "#c9c3bd",
    grid: "#dedad6",
    tooltip: "#ffffff",
  },
  dark: {
    background: "#1e1e1e",
    text: "#e4e4e4",
    mutedText: "#b8b3c4",
    border: "#5a5566",
    grid: "#3b3745",
    tooltip: "#252329",
  },
} as const;

export function getNivoTheme(theme: Theme): NivoTheme {
  const colors = palette[theme];
  return {
    background: colors.background,
    textColor: colors.text,
    fontSize: 12,
    axis: {
      domain: { line: { stroke: colors.border, strokeWidth: 1 } },
      ticks: {
        line: { stroke: colors.border, strokeWidth: 1 },
        text: { fill: colors.mutedText },
      },
      legend: { text: { fill: colors.text } },
    },
    grid: { line: { stroke: colors.grid, strokeWidth: 1 } },
    legends: { text: { fill: colors.text } },
    labels: { text: { fill: colors.text } },
    tooltip: {
      container: {
        background: colors.tooltip,
        color: colors.text,
        border: `1px solid ${colors.border}`,
        borderRadius: 4,
        boxShadow: "0 4px 12px rgb(0 0 0 / 22%)",
      },
    },
  };
}

export function useNivoTheme(): NivoTheme {
  const [theme] = useTheme();
  return React.useMemo(() => getNivoTheme(theme), [theme]);
}
