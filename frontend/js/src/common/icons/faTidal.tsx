import {
  IconDefinition,
  IconName,
  IconPrefix,
} from "@fortawesome/fontawesome-svg-core";

// Tidal brand mark: 4 equal diamonds — 3 in top row + 1 below center
export const faTidal: IconDefinition = {
  prefix: "fab" as IconPrefix,
  iconName: "tidal" as IconName,
  icon: [
    512,
    512,
    [],
    "",
    "M96 96 L176 176 L96 256 L16 176 Z M256 96 L336 176 L256 256 L176 176 Z M416 96 L496 176 L416 256 L336 176 Z M256 256 L336 336 L256 416 L176 336 Z",
  ],
};

export default faTidal;
