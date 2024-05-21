import * as React from "react";

import { useLocation, Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ExportButtons from "../export/ExportButtons";

export default function DeleteListens() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const location = useLocation();
  const navigate = useNavigate();

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
      if (!response.ok) {
        const errJson = await response.json();
        throw errJson.message ?? "Error";
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
              <button
                type="button"
                onClick={() => {
                  navigate("/settings/");
                }}
              >
                Back to setting
              </button>
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

      <p>
        The listens will not be recoverable. Please consider exporting your
        ListenBrainz data before deleting your account.
      </p>

      <ExportButtons feedback={false} />
      <br />

      <form onSubmit={deleteListens}>
        <button
          id="btn-delete-listens"
          className="btn btn-danger btn-lg"
          type="submit"
          style={{ width: "250px" }}
        >
          Delete listens
        </button>
      </form>
    </>
  );
}
