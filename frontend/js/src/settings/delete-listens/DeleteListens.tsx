import * as React from "react";

import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import NiceModal from "@ebay/nice-modal-react";
import { isString } from "lodash";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ExportButtons from "../export/ExportButtons";
import ConfirmationModal from "../../components/ConfirmationModal";

export default function DeleteListens() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const navigate = useNavigate();

  // eslint-disable-next-line consistent-return
  const deleteListens = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    try {
      const confirmMessage = (
        <>
          <span className="text-danger">
            You are about to delete all of your listens.
          </span>
          <br />
          <b>This action cannot be undone.</b>
          <br />
          Are you certain you want to proceed?
        </>
      );
      await NiceModal.show(ConfirmationModal, { body: confirmMessage });
    } catch (error) {
      toast.info("Canceled listen deletion");
      return undefined;
    }
    try {
      const response = await fetch("/settings/delete-listens/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        const errJson = await response.json();
        throw isString(errJson.error)
          ? errJson.error
          : errJson.toString() || "Error";
      }

      toast.success(
        <ToastMsg
          title="Success"
          message="Your listens have been enqueued for deletion. Please note your listens will still be visible for up to an hour."
        />
      );

      setTimeout(() => {
        navigate(`/user/${name}/`);
      }, 3000);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={
            <>
              Error while deleting listens for user {name}: {error.toString()}
            </>
          }
        />
      );

      return navigate("/settings/");
    }
  };

  return (
    <>
      <Helmet>
        <title>Delete Listens</title>
      </Helmet>
      <h3 className="page-title">Delete listens: {name}</h3>
      <p>
        <b>Deleted listens are not recoverable.</b> Consider exporting your
        ListenBrainz data before deleting your account.
      </p>

      <ExportButtons feedback={false} />
      <br />

      <p>
        <b>
          This will permanently delete all ListenBrainz listens for user {name}.
        </b>
      </p>

      <p>
        If you are still connected to Spotify, the last 50 Spotify tracks may be
        auto-reimported. You can{" "}
        <Link to="/settings/music-services/details/">Disconnect</Link> Spotify
        before deleting.
      </p>

      <button
        id="btn-delete-listens"
        className="btn btn-danger btn-lg"
        type="button"
        style={{ width: "250px" }}
        onClick={deleteListens}
        data-toggle="modal"
        data-target="#ConfirmationModal"
      >
        Delete listens
      </button>
    </>
  );
}
