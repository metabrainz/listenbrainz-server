import * as React from "react";

import { redirect, useLocation, Link } from "react-router-dom";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { downloadFile } from "../export/ExportData";

export default function DeleteListens() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const location = useLocation();
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

  // eslint-disable-next-line consistent-return
  const deleteListens = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

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
          message="Your listens have been deleted. You will be logged out in 5 seconds."
        />
      );

      // TODO: Should be replaced by redirect using react-router-dom
      setTimeout(() => {
        window.location.href = `/user/${name}/`;
      }, 3000);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Error while deleting listens for user ${name}`}
        />
      );

      return redirect("/settings/");
    }
  };

  return (
    <>
      <h3 className="page-title">Delete your listens</h3>
      <p>
        Hi {name}, are you sure you want to delete listens imported into your
        ListenBrainz account?
      </p>

      <p>Once deleted, all your listens data will be removed PERMANENTLY.</p>

      <p>
        Warning: if you are still connected to Spotify, the last 50 Spotify tracks might be auto-reimported. <Link to="/settings/music-services/details/">Disconnect</Link> before deleting. 
      </p>

      <p>
        Note: you can export your ListenBrainz data before deleting your
        listens.
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
      <br />
      <p>Yes, I am sure I want to erase my entire listening history</p>

      <form onSubmit={deleteListens}>
        <button
          id="btn-delete-listens"
          className="btn btn-danger btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Delete my listens.
        </button>
      </form>
    </>
  );
}
