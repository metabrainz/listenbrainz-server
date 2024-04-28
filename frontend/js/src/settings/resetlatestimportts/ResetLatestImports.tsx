import * as React from "react";

import { redirect, useLocation } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";

export default function ResetImportTimestamp() {
  const location = useLocation();
  const resetToken = async () => {
    try {
      const response = await fetch(location.pathname, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      toast.success(
        <ToastMsg
          title="Success"
          message="Latest import time reset, we'll now import all your data instead of stopping at your last imported listen."
        />
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message="Something went wrong! Unable to reset latest import timestamp right now."
        />
      );
    }
    setTimeout(() => {
      redirect("/settings/");
    }, 3000);
  };
  return (
    <>
      <Helmet>
        <title>Reset import timestamp</title>
      </Helmet>
      <h3 className="page-title">Reset Import Timestamp</h3>
      <p>Are you sure you want to reset your token? </p>

      <p>
        The Last.fm importer only checks for new Last.fm
        listens, since your last Last.fm import. To do this,
        it stores the timestamp of the most recent listen
        submitted in your last import. Resetting the timestamp
        will make the next import check your entire Last.fm
        history. This will not create duplicates in your
        ListenBrainz listen history.
      </p>
      <button
        type="button"
        onClick={resetToken}
        className="btn btn-info btn-lg"
        style={{ width: "200px" }}
      >
        Reset import timestamp token
      </button>
    </>
  );
}
