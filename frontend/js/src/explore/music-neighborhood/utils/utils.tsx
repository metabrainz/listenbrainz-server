import * as React from "react";
import { toast } from "react-toastify";
import { snapdom } from "@zumer/snapdom";
import { ToastMsg } from "../../../notifications/Notifications";

export async function downloadComponentAsImage(
  element: HTMLElement,
  fileName: string
): Promise<void> {
  await snapdom.download(element, {
    format: "png",
    filename: fileName,
    scale: 1,
    quality: 1,
  });
}

export async function copyImageToClipboard(element: HTMLElement) {
  if (!navigator.clipboard) {
    throw new Error("No clipboard functionality detected for this browser");
  }

  if ("write" in navigator.clipboard) {
    const canvas = await snapdom.toCanvas(element, {
      format: "png",
      scale: 1,
      quality: 1,
    });
    canvas.toBlob((blob) => {
      try {
        if (!navigator.clipboard) {
          throw new Error(
            "No clipboard functionality detected for this browser"
          );
        }

        if (!blob) {
          throw new Error("Could not save image file");
        }

        if ("write" in navigator.clipboard) {
          let data: ClipboardItems;
          if ("ClipboardItem" in window) {
            data = [new ClipboardItem({ "image/png": blob })];
          } else {
            // For browers with no support for ClipboardItem
            throw new Error(
              "ClipboardItem is not available. User may be on FireFox with asyncClipboard.clipboardItem disabled"
            );
          }

          navigator.clipboard
            .write(data)
            .then(() => {
              toast.success("Image copied to clipboard");
            })
            .catch((error) => {
              throw error;
            });
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Could not copy image to clipboard"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "copy-image-error" }
        );
      }
    });
  }
}
