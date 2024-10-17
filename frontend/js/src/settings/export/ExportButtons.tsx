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

function renderExport(ex: Export) {
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
          action={`/export/delete/${ex.export_id}/`}
          method="post"
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
      </p>
      {/* {ex.status !== ExportStatus.waiting && progressBar} */}
      <p>
        Once your export is ready we&apos;ll send you an email, and you can
        return to this page to download the zip file.
        <br />
        Feel free to close this page while we prepare your download.
      </p>
      <form
        action={`/export/delete/${ex.export_id}/`}
        method="post"
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
  const [fetchedExport, setFetchedExport] = React.useState<Export>();
  const [exportId, setExportId] = React.useState<number>();

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
            title="There was an error getting your exports in progress."
            message={`Please try again and contact us if the issue persists.
          ${error}`}
          />
        );
      } finally {
        setLoading(false);
      }
    }
    setLoading(true);
    getExportsInProgress();
  }, []);

  React.useEffect(() => {
    // Fetch an export after requesting a new one
    async function fetchExport() {
      try {
        const response = await fetch(`/export/${exportId}/`, {
          method: "GET",
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of exports
        const result = await response.json();
        setFetchedExport(result);
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
    }
    if (exportId) {
      setLoading(true);
      fetchExport();
    }
  }, [exportId]);

  const hasAnExportInProgress =
    exports.findIndex(
      (exp) =>
        exp.type === ExportType.allUserData &&
        exp.status !== ExportStatus.complete
    ) !== -1;

  const createExport = React.useCallback(async () => {
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

      const data = await response.json();
      const { export_id } = data;
      setExportId(export_id);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="TThere was an error creating an export of your data"
          message={`Please try again and contact us if the issue persists.
          ${error}`}
        />
      );
    }
  }, [setExportId]);

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
      {fetchedExport && renderExport(fetchedExport)}
      {exports && exports.map(renderExport)}
    </section>
  );
}
