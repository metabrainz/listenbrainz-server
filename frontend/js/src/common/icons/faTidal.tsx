import {
  IconDefinition,
  IconName,
  IconPrefix,
} from "@fortawesome/fontawesome-svg-core";

/**
 * Custom FontAwesome-compatible icon definition for Tidal
 * Based on Tidal's "T" mark: two stacked triangles forming a wave
 */
export const faTidal: IconDefinition = {
  prefix: "fab" as IconPrefix,
  iconName: "tidal" as IconName,
  icon: [
    512,
    512,
    [],
    "",
    [
      // Outer shape: large downward triangle
      "M0 0L512 0L256 288Z",
      // Inner shape: smaller upward triangle
      "M192 288L320 288L256 512Z",
    ],
  ],
};

export default faTidal;
