import * as React from "react";
import html2canvas from "html2canvas";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";

const saveAs = (blob: string, fileName: string) => {
  const elem = window.document.createElement("a");
  elem.href = blob;
  elem.download = fileName;
  (document.body || document.documentElement).appendChild(elem);
  if (typeof elem.click === "function") {
    elem.click();
  } else {
    elem.target = "_blank";
    elem.dispatchEvent(
      new MouseEvent("click", {
        view: window,
        bubbles: true,
        cancelable: true,
      })
    );
  }
  URL.revokeObjectURL(elem.href);
  elem.remove();
};

export async function componentToImage(
  element: HTMLElement
): Promise<HTMLCanvasElement> {
  const canvas = await html2canvas(element, {
    onclone(clonedDoc) {
      const clonedElement = clonedDoc.getElementById(
        "artist-similarity-graph-container"
      );
      if (clonedElement) {
        clonedElement.style.width = "fit-content";
        clonedElement.style.height = "fit-content";
      }
    },
    logging: true,
    useCORS: true,
    allowTaint: true,
    imageTimeout: 30000,
    width: element.offsetWidth,
    height: element.offsetHeight,
  });
  return canvas;
}

export async function downloadComponentAsImage(
  element: HTMLElement,
  fileName: string
): Promise<void> {
  const canvas = await componentToImage(element);
  const image = canvas.toDataURL("image/png", 1.0);
  saveAs(image, fileName);
}

export async function copyImageToClipboard(element: HTMLElement) {
  if (!navigator.clipboard) {
    throw new Error("No clipboard functionality detected for this browser");
  }

  if ("write" in navigator.clipboard) {
    const canvas = await componentToImage(element);
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
          return;
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