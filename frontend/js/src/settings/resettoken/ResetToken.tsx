import * as React from "react";

import { redirect, useLocation } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";

export default function ResetToken() {
  const location = useLocation();
  const resetToken = async () => {
    try {
      const response = await fetch(location.pathname, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      toast.success(<ToastMsg title="Success" message="Access token reset" />);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message="Something went wrong! Unable to reset token right now."
        />
      );

      redirect("/settings/");
    }
  };
  return (
    <>
      <Helmet>
        <title>Reset token</title>
      </Helmet>
      <h3 className="page-title">Reset token</h3>
      <p>Are you sure you want to reset your token? </p>

      <p>
        If you do, you will need to replace your old token with the newly
        generated token in any of your applications that use your token. The old
        token will stop working immediately. Be sure to update the token
        immediately in your applications to ensure that you have no disruptions
        in recording your listens.
      </p>
      <button
        type="button"
        onClick={resetToken}
        className="btn btn-info btn-lg"
        style={{ width: "200px" }}
      >
        Yes, change it
      </button>
    </>
  );
}
