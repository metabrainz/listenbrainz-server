import * as React from "react";

import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";

export const downloadFile = async (url: string) => {
  const response = await fetch(url, {
    method: "POST",
  });
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

export default function Export() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const downloadListens = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      await downloadFile(window.location.href);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to download listens: ${error}`}
        />
      );
    }
  };

  const downloadFeedback = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      await downloadFile("/settings/export-feedback/");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to download feedback: ${error}`}
        />
      );
    }
  };

  return (
    <>
      <Helmet>
        <title>Export for {currentUser?.name}</title>
      </Helmet>
      <h3>Export from ListenBrainz</h3>
      <p>Export and download your listen history in JSON format.</p>
      <form onSubmit={downloadListens}>
        <button className="btn btn-warning btn-lg" type="submit">
          Download listens
        </button>
      </form>
      <br />
      <p>
        Export and download your recording feedback (your loved and hated
        recordings) in JSON format.
      </p>
      <form onSubmit={downloadFeedback}>
        <button className="btn btn-warning btn-lg" type="submit">
          Download feedback
        </button>
      </form>
    </>
  );
}
