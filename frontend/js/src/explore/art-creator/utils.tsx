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
  // Strip the a:visited CSS rule before Canvg - it resolves 'fill: inherit'
  // to black (SVG initial value) instead of the parent's computed CSS fill.
  // The rule is only needed for browser rendering (Chromium bug #40356084).
  const cleanedSvg = svgString.replace(
    /a,\s*a:visited,\s*a:link,\s*a:hover\s*\{[^}]*\}/g,
    ""
  );
  const v = Canvg.fromString(ctx as RenderingContext2D, cleanedSvg, {
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

// Font options dictionary pending LB-TBD for full font selection support
export const fontOptions: Record<string, string> = {
  Sintony: "sintony",
  Inter: "inter",
  Roboto: "roboto",
  Oswald: "oswald",
  "Space Grotesk": "space-grotesk",
  "Playfair Display": "playfair-display",
  Lora: "lora",
  "Bebas Neue": "bebas-neue",
};

export const DEFAULT_FONT = "Sintony";

export function buildFontStyleBlock(fontFamily: string): string {
  const fontFile =
    fontOptions[fontFamily] ?? fontFamily.toLowerCase().replace(/\s+/g, "-");
  const fontUrl = `${window.location.origin}/static/fonts/${fontFile}.woff2`;
  return `
      <style>
        @font-face {
          font-family: "${fontFamily}";
          src: url("${fontUrl}") format("woff2");
          font-weight: normal;
          font-style: normal;
        }
      </style>
    `;
}

export function getCombinedCaptionBgColor(
  colorHex: string,
  opacityPercent: number
): string {
  const hex = colorHex.replace("#", "");
  const alphaByte = Math.min(
    255,
    Math.max(0, Math.round((opacityPercent / 100) * 255))
  );
  const alphaHex = alphaByte.toString(16).padStart(2, "0");
  return `#${hex}${alphaHex}`;
}

export function prepareSvgForExport(
  svgElement: SVGSVGElement,
  isGrid: boolean,
  captionOptions: {
    showCaption: boolean;
    showRank: boolean;
    showArtist: boolean;
    showRelease: boolean;
    showListenCount: boolean;
    captionTextColor: string;
    captionBgColor: string;
    captionBgOpacity: number;
  },
  fontFamily: string
): string {
  const clone = svgElement.cloneNode(true) as SVGSVGElement;

  // Strip the preview-only <style> tag injected by Preview.tsx
  // This removes !important CSS and 8-digit hex colors that Canvg cannot parse.
  clone.querySelectorAll("style").forEach((styleEl) => styleEl.remove());

  if (isGrid) {
    if (!captionOptions.showCaption) {
      clone.querySelectorAll(".caption").forEach((el) => {
        el.setAttribute("display", "none");
      });
    } else {
      const opacityVal = (captionOptions.captionBgOpacity / 100).toFixed(2);
      clone.querySelectorAll(".caption rect").forEach((rect) => {
        rect.setAttribute("fill", captionOptions.captionBgColor);
        rect.setAttribute("fill-opacity", opacityVal);
      });

      clone
        .querySelectorAll(
          ".caption text tspan, .caption path.caption-listen-count"
        )
        .forEach((el) => {
          el.setAttribute("fill", captionOptions.captionTextColor);
        });

      if (!captionOptions.showRank) {
        clone.querySelectorAll(".caption-rank").forEach((el) => {
          el.setAttribute("display", "none");
        });
      }
      if (!captionOptions.showArtist) {
        clone.querySelectorAll(".caption-artist").forEach((el) => {
          el.setAttribute("display", "none");
        });
      }
      if (!captionOptions.showRelease) {
        clone.querySelectorAll(".caption-release").forEach((el) => {
          el.setAttribute("display", "none");
        });
      }
      if (!captionOptions.showListenCount) {
        clone.querySelectorAll(".caption-listen-count").forEach((el) => {
          el.setAttribute("display", "none");
        });
      }
    }
  }

  let svgString = clone.outerHTML;

  // Prepend @font-face block after preview style tag has been removed
  const styleBlock = buildFontStyleBlock(fontFamily);
  svgString = svgString.replace(/>/, `>${styleBlock}`);

  return svgString;
}
