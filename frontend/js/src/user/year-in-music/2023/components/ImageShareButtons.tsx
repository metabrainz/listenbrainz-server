/* eslint-disable no-console */
import {
  faCircleCheck,
  faCopy,
  faDownload,
  faShareAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Canvg } from "canvg";
import { saveAs } from "file-saver";
import { toast } from "react-toastify";
import { ToastMsg } from "../../../../notifications/Notifications";

export type MagicShareButtonProps = {
  svgURL: string;
  shareUrl: string;
  shareTitle: string;
  shareText?: string;
  fileName: string;
  customStyles?: string;
};

export default function MagicShareButton({
  svgURL,
  shareUrl,
  shareTitle,
  shareText,
  fileName,
  customStyles,
}: MagicShareButtonProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [copySuccess, setCopySuccess] = useState(false);

  const hasShareFunctionality = Boolean(navigator.canShare);

  const getSVG = React.useMemo(
    () => async (): Promise<Blob | null | undefined> => {
      let fetchedSvgString;
      const canvas = canvasRef.current;
      try {
        const response = await fetch(svgURL);
        fetchedSvgString = await response.text();
        if (!response.ok) {
          throw Error(fetchedSvgString);
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Failed to load image"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />
        );
        return undefined;
      }
      if (customStyles) {
        // inject optional custom styles into the SVG string
        fetchedSvgString = fetchedSvgString.replace(
          /(?=<\/style>)/gm,
          customStyles
        );
      }

      const ctx = canvas?.getContext("2d", { alpha: false });
      if (!ctx || !fetchedSvgString) {
        return undefined;
      }
      const v = Canvg.fromString(ctx, fetchedSvgString, {
        anonymousCrossOrigin: true,
      });
      // Start SVG rendering
      await v.render({
        ignoreDimensions: false,
      });
      // toBlob uses a callback function but we want to await a promise instead
      const theBlob = await new Promise<Blob | undefined>((resolve) => {
        canvas?.toBlob((blob) => {
          if (blob) {
            resolve(blob);
          } else {
            console.debug("Canvas element was not able to produce a blob");
            resolve(undefined);
          }
        });
      });
      return theBlob;
    },
    [svgURL, customStyles]
  );

  const saveToFile = useCallback(async () => {
    const blob = await getSVG();
    if (!blob) {
      console.debug("No blob, returning");
      toast.error(
        <ToastMsg
          title="Something went wrong…"
          message="but we don't know what. Sorry for the inconvenience."
        />
      );
      return;
    }
    saveAs(blob, fileName);
  }, [fileName, getSVG]);

  const copyToClipboard = useCallback(async () => {
    if (!("ClipboardItem" in window)) {
      toast.error(
        <ToastMsg
          title="'I'm sorry, Dave. I'm afraid I can't do that.'"
          message="Your browser doesn't allow copying to clipboard"
        />
      );
      return;
    }
    const blob = await getSVG();
    if (!blob) {
      console.debug("No blob, returning");
      toast.error(
        <ToastMsg
          title="Something went wrong…"
          message="but we don't know what. Sorry for the inconvenience."
        />
      );
      return;
    }
    const data = [new ClipboardItem({ [blob.type]: blob })];
    await navigator.clipboard
      .write(data)
      .then(() => {
        setCopySuccess(true);
        setTimeout(() => {
          setCopySuccess(false);
        }, 3000);
      })
      .catch((error) => {
        toast.error(
          <ToastMsg
            title="Error copying image"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />
        );
      });
  }, [getSVG]);

  const shareWithAPI = useCallback(async () => {
    const blob = await getSVG();
    if (!blob) {
      console.debug("No blob, returning");
      toast.error(
        <ToastMsg
          title="Something went wrong…"
          message="but we don't know what. Sorry for the inconvenience."
        />
      );
      return;
    }
    const canvas = canvasRef.current;
    const image = canvas?.toDataURL();
    if (!image) {
      return;
    }

    // Convert dataUrl into blob using browser fetch API
    // const blob = await (await fetch(image)).blob();
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
        toast.error(
          <ToastMsg
            title="Error sharing image"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />
        );
        // Fallback to saving the image
        saveToFile();
      });
    } else {
      toast.error(
        <ToastMsg
          title="'I'm sorry, Dave. I'm afraid I can't do that.'"
          message="The Share API is not supported or not enabled on this browser"
        />
      );
      // Fallback to saving the image
      saveToFile();
    }
  }, [
    getSVG,
    fileName,
    shareTitle,
    shareUrl,
    shareText,
    hasShareFunctionality,
    saveToFile,
  ]);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{ display: "none" }}
        width="924"
        height="924"
      />
      <div>
        <button
          className="yim-share-button btn btn-icon btn-info"
          disabled={!hasShareFunctionality}
          type="button"
          onClick={shareWithAPI}
          title="Share"
        >
          <FontAwesomeIcon fixedWidth icon={faShareAlt} />
        </button>
        <button
          className="yim-share-button btn btn-icon btn-info"
          type="button"
          onClick={copyToClipboard}
          title="Copy to clipboard"
        >
          <FontAwesomeIcon
            fixedWidth
            icon={copySuccess ? faCircleCheck : faCopy}
          />
        </button>
        <button
          className="yim-share-button btn btn-icon btn-info"
          type="button"
          onClick={saveToFile}
          title="Save as…"
        >
          <FontAwesomeIcon fixedWidth icon={faDownload} />
        </button>
      </div>
    </>
  );
}
