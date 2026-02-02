import { Canvg, RenderingContext2D, presets } from "canvg";

const offscreenPreset = presets.offscreen();
export async function svgToBlob(
  width: number,
  height: number,
  svgString: string,
  encodeType: string = "image/png"
): Promise<Blob> {
  let canvas: OffscreenCanvas | HTMLCanvasElement;
  if ("OffscreenCanvas" in window) {
    // Not supported everywhere: https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas#browser_compatibility
    canvas = new OffscreenCanvas(width, height);
  } else {
    canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("No canvas context");
  }
  const v = Canvg.fromString(ctx as RenderingContext2D, svgString, {
    ...offscreenPreset,
    // Overwrite the Canvg typescript types here, replace once this Canvg ticket is resolved:
    // https://github.com/canvg/canvg/issues/1754
    createCanvas: offscreenPreset.createCanvas as () => OffscreenCanvas & {
      getContext(contextId: "2d"): OffscreenCanvasRenderingContext2D;
    },
  });

  // Render only first frame, ignoring animations and mouse.
  await v.render();

  let blob;
  if ("OffscreenCanvas" in window) {
    canvas = canvas as OffscreenCanvas;
    blob = await canvas.convertToBlob({
      type: encodeType,
    });
  } else {
    blob = await new Promise<Blob | null>((done, err) => {
      try {
        canvas = canvas as HTMLCanvasElement;
        canvas.toBlob(done, encodeType);
      } catch (error) {
        err(error);
      }
    });
    if (blob === null) {
      throw new Error(
        "No image to copy. This is most likely due to a canvas rendering issue in your browser"
      );
    }
  }
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
