import * as React from "react";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRightLong,
  faChevronCircleRight,
  faRefresh,
} from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../../../notifications/Notifications";
import Loader from "../../../../components/Loader";
import GlobalAppContext from "../../../../utils/GlobalAppContext";

type ImportStatusProps = {
  serviceName: ImportService;
};
export enum ImportStatusT {
  inProgress = "Importing",
  complete = "Synced",
}
export default function ImportStatus({ serviceName }: ImportStatusProps) {
  const [loading, setLoading] = React.useState(false);
  const [
    importData,
    setImportData,
  ] = React.useState<LatestImportResponse | null>(null);
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const fetchStatus = React.useCallback(async () => {
    if (!currentUser) {
      return;
    }
    setLoading(true);
    setImportData(null);
    try {
      const data = await APIService.getLatestImport(
        currentUser.name,
        serviceName
      );
      setImportData(data);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="There was an error getting your import's status."
          message={`Please try again and contact us if the issue persists.
              ${error}`}
        />
      );
    } finally {
      setLoading(false);
    }
  }, [APIService, currentUser, serviceName]);

  React.useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  let bsColorClass = "secondary";
  if (importData?.status?.state === ImportStatusT.complete) {
    bsColorClass = "success";
  } else if (importData?.status?.state === ImportStatusT.inProgress) {
    bsColorClass = "info";
  }

  const statusString = importData?.status?.state ?? "N/A";

  return (
    <div className={`alert alert-${bsColorClass}`} role="alert">
      <details>
        <summary>
          <h4 className="alert-heading align-items-center d-flex m-0">
            <FontAwesomeIcon
              icon={faChevronCircleRight}
              size="sm"
              className="summary-indicator"
            />
            Import status{importData?.status?.state ? `: ${statusString}` : ""}
            <button
              type="button"
              className={`btn btn-sm btn-outline-${bsColorClass} ms-auto`}
              onClick={fetchStatus}
              disabled={loading}
              title="Refresh status"
            >
              <FontAwesomeIcon icon={faRefresh} spin={loading} />
            </button>
          </h4>
        </summary>
        <div className="alert-body">
          {loading && (
            <div style={{ textAlign: "center", margin: "1em 0" }}>
              <Loader isLoading={loading} />
            </div>
          )}

          {!loading && !importData && (
            <p className="text-muted">No active import data found.</p>
          )}

          {!loading && importData && (
            <dl className="row mt-3">
              <div className="col">
                <dt>Listens Imported:</dt>
                <dd>{importData?.status?.count ?? 0}</dd>
                <dt>Last imported listen date:</dt>
                <dd>
                  {new Date(
                    (importData?.latest_import ?? 0) * 1000
                  ).toLocaleString()}
                </dd>
              </div>
              <div className="col">
                <dt>Service:</dt>
                <dd>{serviceName}</dd>
                <dt>Status:</dt>
                <dd>{importData?.status?.state ?? "N/A"}</dd>
              </div>
            </dl>
          )}
        </div>
      </details>
    </div>
  );
}
