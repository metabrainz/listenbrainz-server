/* eslint-disable no-useless-escape */
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

// Note: This UUID regexp has a capturing group but no start or end of string character to make it reusable
const uuid = "([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})"
// Note: These website URL regexps have a start of string character (^) but no end of string ($)
const musicbrainz_website_regex = "^(?:https?:\/\/)?(?:beta\.)?musicbrainz\.org"
const listenbrainz_website_regex = "^(?:https?:\/\/)?(?:beta\.)?listenbrainz\.org"
// Note: adding a start-of-string and end-of-string character for UUID_REGEXP
export const UUID_REGEXP = new RegExp(`^${uuid}$`,"i");
export const RECORDING_MBID_REGEXP = new RegExp(`${musicbrainz_website_regex}\/recording\/${uuid}\/?`, "i");
export const RELEASE_MBID_REGEXP = new RegExp(`${musicbrainz_website_regex}\/release\/${uuid}\/?`, "i");
export const RELEASE_GROUP_MBID_REGEXP = new RegExp(`${musicbrainz_website_regex}\/release-group\/${uuid}\/?`, "i");
export const LB_ALBUM_MBID_REGEXP = new RegExp(`${listenbrainz_website_regex}\/album\/${uuid}\/?`, "i");