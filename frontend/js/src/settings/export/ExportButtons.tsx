import * as React from "react";

import { toast } from "react-toastify";
import { startCase } from "lodash";
import { format } from "date-fns";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRightLong,
  faCancel,
  faChevronCircleRight,
  faDownload,
  faRefresh,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../notifications/Notifications";
import Loader from "../../components/Loader";

enum ExportType {
  allUserData = "export_all_user_data",
}
enum ExportStatus {
  inProgress = "in_progress",
  waiting = "waiting",
  complete = "completed",
  failed = "failed",
}
type Export = {
  export_id: number;
  type: ExportType;
  available_until: string | null;
  created: string;
  progress: string;
  filename: string | null;
  status: ExportStatus;
};

function renderExport(
  ex: Export,
  deleteExport: (event: React.SyntheticEvent, exportToDeleteId: number) => void,
  fetchExport: (exportId: number) => Promise<any>
) {
  const extraInfo = (
    <p>
      <details>
        <summary>
          <FontAwesomeIcon icon={faChevronCircleRight} size="sm" /> Details
        </summary>
        <dl className="row">
          <dt className="col-xs-4">Progress</dt>
          <dd className="col-xs-8">{ex.progress}</dd>
          <dt className="col-xs-4">Type</dt>
          <dd className="col-xs-8">{startCase(ex.type)}</dd>
          <dt className="col-xs-4">Requested on</dt>
          <dd className="col-xs-8">{format(ex.created, "PPp")}</dd>
          <dt className="col-xs-4">Export #</dt>
          <dd className="col-xs-8">{ex.export_id}</dd>
        </dl>
      </details>
    </p>
  );
  if (ex.status === ExportStatus.complete) {
    return (
      <div className="mt-15 alert alert-success" role="alert">
        <h4 className="alert-heading">Export ready to download</h4>
        <form
          action={`/export/download/${ex.export_id}/`}
          method="post"
          className="mb-10"
        >
          <button
            type="submit"
            name="download_export"
            className="btn btn-success"
          >
            <FontAwesomeIcon icon={faDownload} />
            &nbsp;Download {ex.filename ?? `${ex.export_id}.zip`}
          </button>
        </form>
        <p>
          <b>
            Note: the file will be deleted automatically after 30 days
            <br />
            {ex.available_until && (
              <small>({format(ex.available_until, "PPPPpppp")})</small>
            )}
          </b>
        </p>
        <form
          onSubmit={(e) => deleteExport(e, ex.export_id)}
          className="mt-10 mb-10"
        >
          <button type="submit" name="delete_export" className="btn btn-danger">
            <FontAwesomeIcon icon={faTrash} />
            &nbsp;Delete export
          </button>
        </form>
        {extraInfo}
      </div>
    );
  }
  if (ex.status === ExportStatus.failed) {
    return (
      <div className="mt-15 alert alert-danger" role="alert">
        <h4 className="alert-heading">Export failed</h4>
        <p>
          There was an error creating an export of your data.
          <br />
          Please try again and contact us if the issue persists.
        </p>
        {extraInfo}
      </div>
    );
  }
  /* const percentage = `${ex.progress}%`;
  const progressBar = (
    <div className="progress">
      <div
        className="progress-bar bg-success"
        role="progressbar"
        aria-valuenow={ex.progress}
        style={{ width: percentage }}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {percentage}
      </div>
    </div>
  ); */
  return (
    <div className="mt-15 alert alert-info" role="alert">
      <h4 className="alert-heading">
        Export in progress
        <br />
      </h4>
      <p className="text-primary">
        <FontAwesomeIcon icon={faArrowRightLong} />
        &nbsp;{ex.progress}
        <button
          type="button"
          className="btn btn-sm btn-transparent"
          onClick={() => {
            fetchExport(ex.export_id);
          }}
        >
          <FontAwesomeIcon icon={faRefresh} />
        </button>
      </p>
      {/* {ex.status !== ExportStatus.waiting && progressBar} */}
      <p>
        Once your export is ready we&apos;ll send you an email, and you can
        return to this page to download the zip file.
        <br />
        Feel free to close this page while we prepare your download.
      </p>
      <form
        onSubmit={(e) => deleteExport(e, ex.export_id)}
        className="mt-10 mb-10"
      >
        <button type="submit" name="cancel_export" className="btn btn-warning">
          <FontAwesomeIcon icon={faCancel} />
          &nbsp;Cancel export
        </button>
      </form>
      {extraInfo}
    </div>
  );
}

export default function ExportButtons({ listens = true, feedback = false }) {
  const [loading, setLoading] = React.useState(false);
  const [exports, setExports] = React.useState<Array<Export>>([]);

  React.useEffect(() => {
    // Fetch the list of exports in progress in background tasks or finished
    async function getExportsInProgress() {
      try {
        const response = await fetch("/export/list/", {
          method: "GET",
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of exports
        const results = await response.json();
        setExports(results);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error retrieving your exports in progress"
            message={`Please try again and contact us if the issue persists.
            Details: ${error}`}
          />
        );
      } finally {
        setLoading(false);
      }
    }
    setLoading(true);
    getExportsInProgress();
  }, []);

  const fetchExport = React.useCallback(
    async function fetchExport(id: number) {
      setLoading(true);
      try {
        const response = await fetch(`/export/${id}/`, {
          method: "GET",
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of exports
        const nexExport = await response.json();
        setExports((prevExports) => {
          // Replace item in exports array, or if not found there
          // place the newly created one at the beginning
          const existingExportIndex = prevExports.findIndex(
            (ex) => ex.export_id === nexExport.export_id
          );
          if (existingExportIndex !== -1) {
            const newArray = [...prevExports];
            newArray.splice(existingExportIndex, 1, nexExport);
            return newArray;
          }
          return [nexExport, ...prevExports];
        });
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error getting your exports in progress."
            message={`Please try again and contact us if the issue persists.
        ${error}`}
          />
        );
      } finally {
        setLoading(false);
      }
    },
    [setLoading]
  );

  const hasAnExportInProgress =
    exports.findIndex(
      (exp) =>
        exp.type === ExportType.allUserData &&
        exp.status !== ExportStatus.complete
    ) !== -1;

  const createExport = React.useCallback(
    async (event: React.SyntheticEvent) => {
      event.preventDefault();
      try {
        const response = await fetch("/export/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }

        const newExport: Export = await response.json();
        setExports((prevExports) => [newExport, ...prevExports]);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error creating an export of your data"
            message={`Please try again and contact us if the issue persists.
          ${error}`}
          />
        );
      }
    },
    []
  );

  const deleteExport = React.useCallback(
    async (event: React.SyntheticEvent, exportToDeleteId: number) => {
      event.preventDefault();
      try {
        const response = await fetch(`/export/delete/${exportToDeleteId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        setExports((prevExports) =>
          prevExports.filter(
            (_export) => _export.export_id !== exportToDeleteId
          )
        );
        toast.info(
          <ToastMsg
            title="Your data export has been canceled"
            message="You can request a new export at any time. If you are experiencing an issue please let us know."
          />
        );
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error canceling your export"
            message={`Please try again and contact us if the issue persists.
           Details: ${error}`}
          />
        );
      }
    },
    []
  );

  return (
    <section id="export-buttons">
      {listens && (
        <>
          <p>
            Export and download your listen history and your feedback
            (love/hate) in JSON format:
          </p>
          <form onSubmit={createExport}>
            <button
              className="btn btn-warning btn-lg"
              type="submit"
              disabled={hasAnExportInProgress}
            >
              Export listens
            </button>
          </form>
          <br />
        </>
      )}
      {/* {feedback && (
        <>
          <p>
            Export and download your recording feedback (your loved and hated
            recordings) in JSON format:
          </p>
          <form onSubmit={downloadFeedback}>
            <button
              className="btn btn-warning btn-lg"
              type="submit"
              disabled={loading}
            >
              Download feedback
            </button>
          </form>{" "}
        </>
      )} */}
      <Loader isLoading={loading} style={{ margin: "0 1em" }} />
      {exports &&
        exports.map((ex) => renderExport(ex, deleteExport, fetchExport))}
    </section>
  );
}
