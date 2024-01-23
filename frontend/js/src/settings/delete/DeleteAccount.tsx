import * as React from "react";

import { redirect } from "react-router-dom";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { downloadFile } from "../export/ExportData";

export default function DeleteAccount() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const downloadListens = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      await downloadFile(window.location.href);
      toast.success(
        <ToastMsg
          title="Success"
          message="Your listens have been downloaded."
        />
      );
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
      toast.success(
        <ToastMsg
          title="Success"
          message="Your feedback have been downloaded.."
        />
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to download feedback: ${error}`}
        />
      );
    }
  };

  // eslint-disable-next-line consistent-return
  const deleteAccount = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      const response = await fetch(window.location.href, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      toast.success(
        <ToastMsg
          title="Success"
          message={`Successfully deleted acount for ${name}.`}
        />
      );

      setTimeout(() => {
        window.location.href = `/`;
      }, 3000);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Error while deleting user ${name}, please try again later.`}
        />
      );

      return redirect("/settings/");
    }
  };

  return (
    <>
      <h3 className="page-title">Delete your account</h3>
      <p>
        Hi {name}, are you sure you want to delete your ListenBrainz account?
      </p>

      <p>
        Once deleted, all your ListenBrainz data will be removed PERMANENTLY and
        will not be recoverable.
      </p>

      <p>
        Note: you can export your ListenBrainz data before deleting your
        account.
      </p>

      <form onSubmit={downloadListens}>
        <button
          className="btn btn-warning btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Export my listens.
        </button>
      </form>

      <form onSubmit={downloadFeedback}>
        <button
          className="btn btn-warning btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Export my feedback.
        </button>
      </form>

      <form onSubmit={deleteAccount}>
        <button
          id="btn-delete-user"
          className="btn btn-danger btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Delete my account.
        </button>
      </form>
    </>
  );
}
