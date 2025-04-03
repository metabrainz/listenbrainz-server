import tinycolor from "tinycolor2";

export function produceRgbShades(
  r: number | string,
  g: number | string,
  b: number | string,
  amount: number
): Array<{ r: number; g: number; b: number }> {
  const shades = [];

  const hsl = tinycolor(`rgb(${r}, ${g}, ${b})`).toHsl();

  for (let i = 9; i > 1; i -= 8 / amount) {
    // Decrements from 9 - 1; i being what luminosity (hsl.l) is multiplied by.
    hsl.l = 0.1 * i;
    shades.push(tinycolor(hsl).toRgb());
  }

  return shades;
}

export function colourToRgbObj(colour: tinycolor.ColorInputWithoutInstance) {
  // TODO: Note which colours tinycolor() can take; i.e. hex / rgb strings, objects, etc.
  return tinycolor(colour).toRgb();
}

export function calculateBounds(min: number, max: number) {
  // i.e. min & max pixels away from the center of the canvas.
  return {
    inside: (cursorPosFromCenter: number) => {
      // our relative mouse-position is passed through here to check.
      return cursorPosFromCenter >= min && cursorPosFromCenter <= max;
    },
  };
}

export function convertObjToString(obj: tinycolor.ColorFormats.RGB) {
  return tinycolor(obj).toRgbString();
}

// Method is helpful for generating a radius representative of the stroke + taking into account lineWidth.
export function getEffectiveRadius(trueRadius: number, lineWidth: number) {
  return trueRadius - lineWidth / 2;
}

export function convertColorReleaseToListen(
  item: ColorReleaseItem
): BaseListenFormat {
  const { release_name, artist_name, release_mbid } = item;
  return {
    listened_at: -1,
    track_metadata: {
      track_name: "",
      artist_name,
      release_name,
      additional_info: {
        release_mbid,
      },
    },
  };
}
