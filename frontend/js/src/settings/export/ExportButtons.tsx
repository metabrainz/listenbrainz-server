import * as React from "react";

import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import Loader from "../../components/Loader";

export const downloadFile = async (url: string) => {
  const response = await fetch(url, {
    method: "POST",
  });
  if (!response.ok) {
    const jsonBody = await response.json();
    throw jsonBody?.error;
  }
  const fileData = await response.blob();
  const filename = response.headers
    ?.get("Content-Disposition")
    ?.split(";")[1]
    .trim()
    .split("=")[1];
  const downloadUrl = URL.createObjectURL(fileData);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.setAttribute("download", filename!);
  link.click();
  URL.revokeObjectURL(downloadUrl);
};

export default function ExportButtons({ listens = true, feedback = true }) {
  const [loading, setLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState();
  const downloadListens = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(undefined);
    try {
      await downloadFile("/settings/export/");
    } catch (error) {
      setErrorMessage(error.toString());
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to download listens: ${error}`}
        />
      );
    }
    setLoading(false);
  };

  const downloadFeedback = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    setLoading(true);
    setErrorMessage(undefined);
    try {
      await downloadFile("/settings/export-feedback/");
    } catch (error) {
      setErrorMessage(error.toString());
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to download feedback: ${error}`}
        />
      );
    }
    setLoading(false);
  };

  return (
    <>
      {listens && (
        <>
          <p>Export and download your listen history in JSON format:</p>
          <form onSubmit={downloadListens}>
            <button
              className="btn btn-warning btn-lg"
              type="submit"
              disabled={loading}
            >
              Download listens
            </button>
          </form>
          <br />
        </>
      )}
      {feedback && (
        <>
          <p>
            Export and download your recording feedback (your loved and hated
            recordings) in JSON format:
          </p>
          <form onSubmit={downloadFeedback}>
            <button
              className="btn btn-warning btn-lg"
              type="submit"
              disabled={loading}
            >
              Download feedback
            </button>
          </form>{" "}
        </>
      )}
      {loading && (
        <div
          className="mt-15 alert alert-info"
          role="alert"
          style={{ maxWidth: "fit-content" }}
        >
          <h4 className="alert-heading">Download started</h4>
          <p className="flex">
            <Loader isLoading={loading} style={{ margin: "0 1em" }} />
            Please keep this page open while your download is being prepared.
            This can take up to a minute.
          </p>
        </div>
      )}
      {errorMessage && (
        <div
          className="mt-15 alert alert-danger alert-dismissable"
          role="alert"
          style={{ maxWidth: "fit-content" }}
        >
          <button
            type="button"
            className="close"
            onClick={() => {
              setErrorMessage(undefined);
            }}
            aria-label="Close"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          <h4 className="alert-heading">Download failed </h4>
          <p>
            Something went wrong with your download. Please try again or let us
            know if the issue persists.
          </p>
          <hr />
          <p className="mb-0">{errorMessage}</p>
        </div>
      )}
    </>
  );
}
