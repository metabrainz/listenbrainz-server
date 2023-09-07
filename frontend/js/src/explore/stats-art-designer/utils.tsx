import { Canvg, presets } from "canvg";

export async function svgToBlob(
  width: number,
  height: number,
  svgString: string,
  encodeType: string = "image/png"
): Promise<Blob> {
  const canvas = new OffscreenCanvas(width, height);

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("No canvas context");
  }
  const v = await Canvg.from(ctx, svgString, presets.offscreen());

  // Render only first frame, ignoring animations and mouse.
  await v.render();

  const blob = await canvas.convertToBlob({ type: encodeType });
  return blob;
}
export async function toPng(
  width: number,
  height: number,
  svgString: string
): Promise<string> {
  const blob = await svgToBlob(width, height, svgString, "image/png");
  if (!blob) {
    throw new Error("Could not save image file");
  }
  const pngUrl = URL.createObjectURL(blob);

  return pngUrl;
}
