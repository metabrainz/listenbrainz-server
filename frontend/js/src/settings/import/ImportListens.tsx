import * as React from "react";

import { Link, useLoaderData } from "react-router";
import { Helmet } from "react-helmet";
import ReactTooltip from "react-tooltip";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRightLong,
  faCancel,
  faChevronCircleRight,
  faRefresh,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { format } from "date-fns";
import GlobalAppContext from "../../utils/GlobalAppContext";
import * as React from "react";
import { ToastMsg } from "../../notifications/Notifications";

type ImportListensLoaderData = {
  user_has_email: boolean;
};

enum ImportStatus {
  inProgress = "in_progress",
  waiting = "waiting",
  complete = "completed",
  failed = "failed",
  cancelled = "cancelled",
}
type Import = {
  import_id: number;
  created: string;
  progress: string;
  filename: string | null;
  status: ImportStatus;
};


function renderImport(
  im: Import,
  cancelImport: (event: React.SyntheticEvent, importToCancelId: number) => void,
  fetchImport: (importId: number) => Promise<any>
) {
  const extraInfo = (
    <p>
      <details>
        <summary>
          <FontAwesomeIcon
            icon={faChevronCircleRight}
            size="sm"
            className="summary-indicator"
          />
          Details
        </summary>
        <dl className="row">
          <dt className="col-4">Progress</dt>
          <dd className="col-8">{im.progress}</dd>
          <dt className="col-4">Requested on</dt>
          <dd className="col-8">{format(im.created, "PPp")}</dd>
          <dt className="col-4">Import #</dt>
          <dd className="col-8">{im.import_id}</dd>
        </dl>
      </details>
    </p>
  );
  if (im.status === ImportStatus.complete) {
    return (
      <div className="mt-4 alert alert-success" role="alert">
        <h4 className="alert-heading">Import completed!</h4>
        
        <p>
          <b>
            Note: the uploaded file(s) will be deleted automatically after the import
          </b>
        </p>
        <form
          onSubmit={(e) => cancelImport(e, im.import_id)}
          className="mt-3 mb-3"
        >
          <button type="submit" name="cancel_import" className="btn btn-danger">
            <FontAwesomeIcon icon={faTrash} />
            &nbsp;Cancel import
          </button>
        </form>
        {extraInfo}
      </div>
    );
  }
  if (im.status === ImportStatus.failed) {
    return (
      <div className="mt-4 alert alert-danger" role="alert">
        <h4 className="alert-heading">Import failed</h4>
        <p>
          There was an error importing your data.
          <br />
          Please try again and contact us if the issue persists.
        </p>
        {extraInfo}
      </div>
    );
  }

  return (
    <div className="mt-4 alert alert-info" role="alert">
      <h4 className="alert-heading">
        Import in progress
        <br />
      </h4>
      <p className="text-primary">
        <FontAwesomeIcon icon={faArrowRightLong} />
        &nbsp;{im.progress}
        <button
          type="button"
          className="btn btn-sm btn-transparent"
          onClick={() => {
            fetchImport(im.import_id);
          }}
        >
          <FontAwesomeIcon icon={faRefresh} />
        </button>
      </p>
      <p>
        Feel free to close this page while we import your listens.
      </p>
      <form
        onSubmit={(e) => cancelImport(e, im.import_id)}
        className="mt-3 mb-3"
      >
        <button type="submit" name="cancel_import" className="btn btn-warning">
          <FontAwesomeIcon icon={faCancel} />
          &nbsp;Cancel import
        </button>
      </form>
      {extraInfo}
    </div>
  );
}


export default function ImportListens() {
  const data = useLoaderData() as ImportListensLoaderData;
  const { user_has_email: userHasEmail } = data;

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const handleListensSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    if (event) event.preventDefault();

    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);
    const file = formData.get("file") as File;
    const service = formData.get("service") as string;
    const from_date = formData.get("from_date") as string | null;
    const to_date = formData.get("to_date") as string | null;

    if (!currentUser?.auth_token) {
      console.error("No auth token available");
      return;
    }
    try {
      const status = await APIService.importListens(
        currentUser?.auth_token,
        formData
      );

      console.log("Import req sent. Status:", status);
    } catch (err) {
      console.error("Import req failed:", err);
    }
  };

  const [loading, setLoading] = React.useState(false);
  const [imports, setImports] = React.useState<Array<Import>>([]);

  React.useEffect(() => {
    // Fetch the list of imports in progress in background tasks or finished
    async function getImportsInProgress() {
      try {
        const response = await fetch("/import-listens/list/", {
          method: "GET",
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of imports
        const results = await response.json();
        setImports(results);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error retrieving your imports in progress"
            message={`Please try again and contact us if the issue persists.
            Details: ${error}`}
          />
        );
      } finally {
        setLoading(false);
      }
    }
    setLoading(true);
    getImportsInProgress();
  }, []);

  const fetchImport = React.useCallback(
    async function fetchImport(id: number) {
      setLoading(true);
      try {
        const response = await fetch(`/import-listens/${id}/`, {
          method: "GET",
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of imports
        const nexImport = await response.json();
        setImports((prevImports) => {
          // Replace item in imports array, or if not found there
          // place the newly created one at the beginning
          const existingImportIndex = prevImports.findIndex(
            (im) => im.import_id === nexImport.import_id
          );
          if (existingImportIndex !== -1) {
            const newArray = [...prevImports];
            newArray.splice(existingImportIndex, 1, nexImport);
            return newArray;
          }
          return [nexImport, ...prevImports];
        });
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error getting your imports in progress."
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

  const hasAnImportInProgress =
    imports.findIndex(
      (imp) =>
        imp.status !== ImportStatus.complete
    ) !== -1;

  const createImport = React.useCallback(
    async (event: React.SyntheticEvent) => {
      event.preventDefault();
      try {
        const response = await fetch("/import-listens/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }

        const newImport: Import = await response.json();
        setImports((prevImports) => [newImport, ...prevImports]);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error creating an import of your data"
            message={`Please try again and contact us if the issue persists.
          ${error}`}
          />
        );
      }
    },
    []
  );

  const cancelImport = React.useCallback(
    async (event: React.SyntheticEvent, importToCancelId: number) => {
      event.preventDefault();
      try {
        const response = await fetch(`/import-listens/cancel/${importToCancelId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        setImports((prevImports) =>
          prevImports.filter(
            (_import) => _import.import_id !== importToCancelId
          )
        );
        toast.info(
          <ToastMsg
            title="Your data import has been cancelled"
            message="You can request a new import at any time. If you are experiencing an issue please let us know."
          />
        );
      } catch (error) {
        toast.error(
          <ToastMsg
            title="There was an error cancelling your import"
            message={`Please try again and contact us if the issue persists.
           Details: ${error}`}
          />
        );
      }
    },
    []
  );

  return (
    <>
      <Helmet>
        <title>Import listens for {currentUser?.name}</title>
      </Helmet>
      <h2 className="page-title">Import your listening history</h2>
      {!userHasEmail && (
        <div className="alert alert-danger">
          You have not provided an email address. Please provide an{" "}
          <a href="https://musicbrainz.org/account/edit">email address</a> and{" "}
          <em>verify it</em> to submit listens. Read this{" "}
          <a href="https://blog.metabrainz.org/?p=8915">blog post</a> to
          understand why we need your email. You can provide us with an email on
          your{" "}
          <a href="https://musicbrainz.org/account/edit">MusicBrainz account</a>{" "}
          page.
        </div>
      )}
      <p>
        This page allows you to import your{" "}
        <span className="strong" data-tip data-for="info-tooltip">
          listens
        </span>{" "}
        from third-party music services by uploading backup files.
      </p>
      <p className="alert alert-info">
        To connect to a music service and track{" "}
        <strong>
          <em>new</em>
        </strong>{" "}
        listens, head to the{" "}
        <Link to="/settings/music-services/details/">Connect services</Link>{" "}
        page .<br />
        For submitting listens from your music player or devices, check out the{" "}
        <Link to="/add-data/">Submitting data</Link> page.
      </p>
      <p>
        <ReactTooltip id="info-tooltip" place="top">
          Fun Fact: The term <strong>scrobble</strong> is a trademarked term by
          Last.fm, and we cannot use it.
          <br />
          Instead, we use the term <strong>listen</strong> for our data.
        </ReactTooltip>
        For example if you{" "}
        <Link to="/settings/music-services/details/">connect to Spotify</Link>{" "}
        we are limited to retrieving your last 50 listens.
        <br />
        You can however request your{" "}
        <a
          href="https://www.spotify.com/us/account/privacy/"
          target="_blank"
          rel="noopener noreferrer"
        >
          extended streaming history
        </a>
        , which contains your entire listening history, and upload it here. To
        avoid duplicates, be sure to set the appropriate limit date and time.
      </p>

      <h3 className="card-title">Import from Listening History Files</h3>
      <br />
      <p>
        Migrate your listens from different streaming services to Listenbrainz!
      </p>
      <div className="card">
        <div className="card-body">
          <form onSubmit={handleListensSubmit}>
            <div className="flex flex-wrap" style={{ gap: "1em" }}>
              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="datetime">
                  Choose a File:
                </label>
                <input
                  type="file"
                  className="form-control"
                  name="file"
                  accept=".zip,.csv,.json,.jsonl"
                  required
                />
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="datetime">
                  Select Service:
                </label>
                <select className="form-select" name="service" required>
                  <option value="spotify">Spotify</option>
                  <option value="listenbrainz">Listenbrainz</option>
                  <option value="applemusic">Apple Music</option>
                </select>
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="start-datetime">
                  Start import from (optional):
                </label>
                <input
                  type="date"
                  className="form-control"
                  max={new Date().toISOString()}
                  name="from_date"
                  title="Date and time to start import at"
                />
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="end-datetime">
                  End date for import (optional):
                </label>
                <input
                  type="date"
                  className="form-control"
                  max={new Date().toISOString()}
                  name="to_date"
                  title="Date and time to end import at"
                />
              </div>

              <div style={{ flex: 0, alignSelf: "end", minWidth: "15em" }}>
                <button type="submit" className="btn btn-success">
                  Import Listens
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
