import * as React from "react";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRefresh, faTimes } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../../../notifications/Notifications";
import Loader from "../../../../components/Loader";

type ImportStatusInfo = {
  status: string;
  listens_imported: number;
};
type ImportStatusProps = {
  onClose: () => void;
  serviceName: string;
  totalListens: number;
};

export default function ImportStatus({
  onClose,
  serviceName,
  totalListens,
}: ImportStatusProps) {
  const [loading, setLoading] = React.useState(false);
  const [importData, setImportData] = React.useState<ImportStatusInfo | null>(
    null
  );

  const fetchStatus = React.useCallback(async () => {
    setLoading(true);
    setImportData(null);
    try {
      const response = await fetch(
        `/settings/music-services/${serviceName}/import-status/`,
        {
          method: "GET",
        }
      );
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
      } else {
        const data: ImportStatusInfo = await response.json();
        setImportData(data || null);
      }
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
  }, [serviceName]);

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

            <dd className="col-xs-8">{importData.status}</dd>

            <dt className="col-xs-4">Listens Imported:</dt>
            <dd className="col-xs-8">{importData.listens_imported}</dd>

            <dt className="col-xs-4">Import Progress:</dt>
            <dd className="col-xs-8">
              {((importData.listens_imported * 100) / totalListens).toFixed(2)}%
            </dd>
          </dl>
        )}
      </div>
    </div>
  );
}
