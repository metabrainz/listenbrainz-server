/* eslint-disable no-console */
import {
  faCopy,
  faDownload,
  faShareAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Canvg } from "canvg";
import { saveAs } from "file-saver";

export type MagicShareButtonProps = {
  svgURL: string;
  shareUrl: string;
  shareTitle: string;
  shareText?: string;
  fileName: string;
};

export default function MagicShareButton({
  svgURL,
  shareUrl,
  shareTitle,
  shareText,
  fileName,
}: MagicShareButtonProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [svgBlob, setSvgBlob] = useState<Blob>();
  const [copySuccess, setCopySuccess] = useState(false);

  const hasShareFunctionality = Boolean(navigator.canShare);

  useEffect(() => {
    const getSVG = async () => {
      let fetchedSvgString;
      const canvas = canvasRef.current;
      try {
        const response = await fetch(svgURL);
        fetchedSvgString = await response.text();
        if (!response.ok) {
          throw Error(fetchedSvgString);
        }
      } catch (error) {
        console.error("Failed to load save image", error);
        return;
      }

      const ctx = canvas?.getContext("2d", { alpha: false });
      if (!ctx || !fetchedSvgString) {
        return;
      }
      const v = Canvg.fromString(ctx, fetchedSvgString, {
        anonymousCrossOrigin: true,
      });
      // Start SVG rendering
      await v.render({
        ignoreDimensions: true,
      });
      canvas?.toBlob((blob) => {
        if (blob) {
          setSvgBlob(blob);
        }
      });
    };
    getSVG().catch(console.error);
  }, []);

  const saveToFile = useCallback(() => {
    if (!svgBlob) {
      return;
    }
    saveAs(svgBlob, fileName);
  }, [fileName, svgBlob]);

  const copyToClipboard = useCallback(() => {
    if (!svgBlob) {
      return;
    }
    const data = [new ClipboardItem({ [svgBlob.type]: svgBlob })];
    navigator.clipboard
      .write(data)
      .then(() => {
        setCopySuccess(true);
        setTimeout(() => {
          setCopySuccess(false);
        }, 1000);
      })
      .catch((error) => {
        console.error("Error copying image:", error);
      });
  }, [svgBlob]);

  const shareWithAPI = useCallback(async () => {
    const canvas = canvasRef.current;
    const image = canvas?.toDataURL();
    if (!image) {
      return;
    }

    // Convert dataUrl into blob using browser fetch API
    const blob = await (await fetch(image)).blob();
    const file = new File([blob], `${fileName}.png`, {
      type: blob.type,
      lastModified: Date.now(),
    });
    const dataToShare: ShareData = {
      title: shareTitle,
      url: shareUrl,
      files: [file],
    };
    if (shareText) {
      dataToShare.text = shareText;
    }
    // Use the Share API to share the image
    if (hasShareFunctionality && navigator.canShare(dataToShare)) {
      navigator.share(dataToShare).catch((error) => {
        console.error("Error sharing image:", error);
        // Fallback to saving the image
        saveToFile();
      });
    } else {
      console.debug("The Share API is not supported on this browser");
      // Fallback to saving the image
      saveToFile();
    }
  }, [hasShareFunctionality, shareText, shareTitle, shareUrl, fileName]);

  const id = `share-modal-${fileName}`;
  return (
    <>
      {/* Trick to load the font files for use with the SVG render */}
      <span
        style={{
          fontFamily: "Inter, sans-serif",
          opacity: 0,
          position: "fixed",
        }}
      >
        x
      </span>
      <div
        className="modal fade share-modal"
        id={id}
        tabIndex={-1}
        role="dialog"
        aria-labelledby="ShareModalLabel"
        data-backdrop="true"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                aria-label="Close"
                data-dismiss="modal"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="ShareModalLabel">
                Share your stats
              </h4>
            </div>
            <div className="modal-body">
              <canvas
                ref={canvasRef}
                style={{ width: "100%", height: "auto" }}
                width="924"
                height="924"
              />
              <p>
                <button
                  className="btn btn-primary"
                  disabled={!hasShareFunctionality}
                  type="button"
                  onClick={shareWithAPI}
                  title="Share"
                >
                  <FontAwesomeIcon icon={faShareAlt} />
                </button>
                <button
                  className={`btn ${
                    copySuccess ? "btn-success" : "btn-primary"
                  }`}
                  type="button"
                  onClick={copyToClipboard}
                  title="Copy to clipboard"
                >
                  <FontAwesomeIcon icon={faCopy} />
                </button>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={saveToFile}
                  title="Save as…"
                >
                  <FontAwesomeIcon icon={faDownload} />
                </button>
              </p>
            </div>
          </form>
        </div>
      </div>
      <button
        className="yim-share-button btn btn-icon btn-info"
        type="button"
        data-toggle="modal"
        data-target={`#${id}`}
      >
        <FontAwesomeIcon icon={faShareAlt} />
      </button>
    </>
  );
}
