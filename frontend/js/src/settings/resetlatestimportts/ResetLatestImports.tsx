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
        <title>Reset import timestamp- ListenBrainz</title>
      </Helmet>
      <h3 className="page-title">Reset Import Timestamp</h3>
      <p>Are you sure you want to reset your token? </p>

      <p>
        ur last.fm importer keeps track of the listens you&apos;ve imported and
        then only imports new listens added after previous imports. To do this,
        we keep track of the timestamp of the newest listen submitted in your
        last.fm import. By resetting this timestamp, you&apos;ll be able to
        import your entire last.fm data again. However, this will not create
        duplicates in your ListenBrainz listen history.
      </p>
      <button
        type="button"
        onClick={resetToken}
        className="btn btn-info btn-lg"
        style={{ width: "200px" }}
      >
        Yes, reset it
      </button>
    </>
  );
}
