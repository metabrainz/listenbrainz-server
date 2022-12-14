import React, { ForwardedRef, useCallback, useRef } from "react";
import { faShare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Canvg } from "canvg";
import { saveAs } from "file-saver";

export type ShareOrSaveSVGProps = {
  svgURL: string;
  shareUrl: string;
  shareTitle: string;
  shareText: string;
  fileName: string;
};

function ShareOrSaveSVG({
  svgURL,
  shareUrl,
  shareTitle,
  shareText,
  fileName,
}: ShareOrSaveSVGProps) {
  const canvasRef: ForwardedRef<HTMLCanvasElement> = useRef(null);
  const saveToFile = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    canvas.toBlob((blob) => {
      if (!blob) {
        return;
      }
      saveAs(blob, fileName);
    });
  }, [canvasRef, fileName]);

  const saveOrShare = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    let svgString = "";
    try {
      const response = await fetch(svgURL);
      svgString = await response.text();
    } catch (error) {
      console.error("Failed to load save image", error);
    }

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) {
      return;
    }
    const v = Canvg.fromString(ctx, svgString);
    // Start SVG rendering
    await v.render();

    const image = canvas.toDataURL("image/png");
    const file = new File([image], fileName, {
      type: "image/png",
      lastModified: new Date().getTime(),
    });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      navigator
        .share({
          files: [file],
          title: shareTitle,
          text: shareText,
          url: shareUrl,
        })
        .then(() => {
          console.log("Share was successful.");
        })
        .catch((error) => {
          console.log("Sharing failed", error);
        });
    } else {
      saveToFile();
    }
  }, [svgURL, shareUrl, shareTitle, shareText, fileName, canvasRef]);

  return (
    <>
      <button className="btn btn-primary" onClick={saveOrShare} type="button">
        <FontAwesomeIcon icon={faShare} />
      </button>
      <canvas ref={canvasRef} style={{ display: "none" }} />
    </>
  );
}

export default ShareOrSaveSVG;
