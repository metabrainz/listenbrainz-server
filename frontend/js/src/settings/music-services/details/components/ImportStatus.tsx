import * as React from "react";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRefresh, faTimes } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../../../notifications/Notifications";
import Loader from "../../../../components/Loader";
import GlobalAppContext from "../../../../utils/GlobalAppContext";

type ImportStatusProps = {
  onClose: () => void;
  serviceName: ImportService;
};

export default function ImportStatus({
  onClose,
  serviceName,
}: ImportStatusProps) {
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

  return (
    <div className="panel panel-info">
      <div className="panel-heading">
        <div className="pull-right">
          <button
            type="button"
            className="btn btn-default btn-xs"
            onClick={fetchStatus}
            disabled={loading}
            title="Refresh Status"
            style={{ marginLeft: "5px" }}
          >
            <FontAwesomeIcon icon={faRefresh} spin={loading} />
          </button>
          <button
            type="button"
            className="btn btn-danger btn-xs"
            onClick={onClose}
            title="Close Status"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>
        <h3 className="panel-title">Import Status</h3>
      </div>

      <div className="panel-body">
        {loading && (
          <div style={{ textAlign: "center", margin: "1em 0" }}>
            <Loader isLoading={loading} />
          </div>
        )}

        {!loading && !importData && (
          <p className="text-muted">No active import data found.</p>
        )}

        {!loading && importData && (
          <dl className="row">
            <dt className="col-xs-4">Service:</dt>
            <dd className="col-xs-8">{serviceName}</dd>
            <dt className="col-xs-4">Status:</dt>
            <dd className="col-xs-8">{importData.status?.state ?? "N/A"}</dd>
            <dt className="col-xs-4">Listens Imported:</dt>
            <dd className="col-xs-8">{importData.status?.count ?? 0}</dd>
            <dt className="col-xs-4">Timestamp of last imported listen:</dt>
            <dd className="col-xs-8">
              {new Date(importData.latest_import * 1000 ?? 0).toLocaleString()}
            </dd>
          </dl>
        )}
      </div>
    </div>
  );
}
