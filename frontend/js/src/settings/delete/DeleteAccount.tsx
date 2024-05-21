import * as React from "react";

import { redirect } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ExportButtons from "../export/ExportButtons";

export default function DeleteAccount() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;

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
        <b>
          This will permanently delete all ListenBrainz data for user {name}.
        </b>
      </p>

      <p>
        <b>The data will not be recoverable.</b> Please consider exporting your
        ListenBrainz data before deleting your account.
      </p>

      <ExportButtons />
      <br />
      <p className="text-brand text-danger">This cannot be undone!</p>
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
