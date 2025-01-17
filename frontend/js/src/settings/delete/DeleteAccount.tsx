import * as React from "react";

import { redirect } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import NiceModal from "@ebay/nice-modal-react";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ExportButtons from "../export/ExportButtons";
import ConfirmationModal from "../../components/ConfirmationModal";

export default function DeleteAccount() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;

  // eslint-disable-next-line consistent-return
  const deleteAccount = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    try {
      const confirmMessage = (
        <>
          <span className="text-danger">
            You are about to delete your account.
          </span>
          <br />
          <b>This action cannot be undone.</b>
          <br />
          Are you certain you want to proceed?
        </>
      );
      await NiceModal.show(ConfirmationModal, { body: confirmMessage });
    } catch (error) {
      toast.info("Canceled account deletion");
      return undefined;
    }
    try {
      const response = await fetch("/settings/delete/", {
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
        <b>Deleted data is not recoverable.</b> Consider exporting your
        ListenBrainz data before deleting your account.
      </p>

      <ExportButtons />
      <br />
      <p className="text-brand text-danger">This cannot be undone!</p>
      <p>
        <b>
          This will permanently delete all ListenBrainz data for user {name}.
        </b>
      </p>

      <button
        id="btn-delete-user"
        className="btn btn-danger btn-lg"
        type="button"
        style={{ width: "250px" }}
        onClick={deleteAccount}
        data-toggle="modal"
        data-target="#ConfirmationModal"
      >
        Delete account
      </button>
    </>
  );
}
