export const COLOR_WHITE = "#fff";
export const COLOR_BLACK = "#000";
export const COLOR_LB_ASPHALT = "#46433a";
export const COLOR_LB_ORANGE = "#eb743b";
export const COLOR_LB_BLUE = "#353070";
export const COLOR_LB_DARK = "#053b47";
export const COLOR_LB_LIGHT_GRAY = "#8d8d8d";
export const COLOR_LB_GREEN = "#5aa854";

/*
  Start from an enum to get both a label representation (for select dropdown UI)
  and the css class name to be used
*/
// eslint-disable-next-line import/prefer-default-export
export enum FlairEnum {
  None = "",
  Shake = "shake",
  ColorSweep = "lb-colors-sweep",
  LightSweep = "light-sweep",
  Wave = "wave",
  FlipHorizontal = "flip-horizontal",
  FlipVertical = "flip-vertical",
  Flip3D = "flip-3d",
  Extruded = "extruded",
  Underline = "underline",
  Tornado = "tornado",
  Highlighter = "highlighter",
  Anaglyph = "anaglyph",
  Sliced = "sliced",
}
// A union type for the label strings, based on the enum above 
export type FlairName = keyof typeof FlairEnum;
// A union type for the flair css strings, based on the enum values above 
export type Flair = `${FlairEnum}`; 