import * as React from "react";

import { redirect } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { downloadFile } from "../export/ExportData";

export default function DeleteAccount() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const downloadListens = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      await downloadFile("/settings/export/");
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
          message="Your feedback has been downloaded."
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
          message={`Successfully enqueued account deletion for ${name}.`}
        />
      );
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
      <Helmet>
        <title>Delete Account</title>
      </Helmet>
      <h3 className="page-title">Delete account: {name}</h3>
      <p>
        <b>This will permanently delete all ListenBrainz data for user {name}.</b>
      </p>

      <p>
        The data will not be recoverable. Please consider exporting
        your ListenBrainz data before deleting your account.
      </p>

      <form onSubmit={downloadListens}>
        <button
          className="btn btn-warning btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Export listens
        </button>
      </form>

      <form onSubmit={downloadFeedback}>
        <button
          className="btn btn-warning btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Export feedback
        </button>
      </form>

      <form onSubmit={deleteAccount}>
        <button
          id="btn-delete-user"
          className="btn btn-danger btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Delete account
        </button>
      </form>
    </>
  );
}
