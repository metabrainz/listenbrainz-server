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
} from "@fortawesome/free-solid-svg-icons";
import { format, isValid } from "date-fns";
import { useMemo } from "react";
import { initial, last, partition } from "lodash";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";
import Loader from "../../components/Loader";

type ImportListensLoaderData = {
  user_has_email: boolean;
  pg_timezones: Array<[string, string]>;
  user_timezone: string;
};

enum ImportStatus {
  inProgress = "in_progress",
  waiting = "waiting",
  complete = "completed",
  failed = "failed",
  cancelled = "cancelled",
}
enum Services {
  spotify = "Spotify",
  listenbrainz = "Listenbrainz",
  // applemusic = "Apple Music",
  librefm = "Libre.fm",
  panoscrobbler = "PanoScrobbler",
  maloja = "Maloja",
  audioscrobbler = "Audioscrobbler",
}
const acceptedFileTypes = {
  [Services.spotify]: ".zip",
  [Services.listenbrainz]: ".zip",
  // [Services.applemusic]: ".zip",
  [Services.librefm]: ".csv",
  [Services.panoscrobbler]: ".jsonl",
  [Services.maloja]: ".json",
  [Services.audioscrobbler]: ".log",
};
type ImportMetadata = {
  filename: string;
  progress: string;
  status: ImportStatus;
  attempted_count?: number;
  success_count?: number;
};
const serviceNames = Object.values(Services);
const humanReadableServices = `${initial(serviceNames).join(", ")} and ${last(
  serviceNames
)}`;
const [zipServices, nonZipServices] = partition(serviceNames, (serv) => {
  return acceptedFileTypes[serv] === ".zip";
});

type Import = {
  import_id: number;
  created: string;
  file_path: string;
  metadata: ImportMetadata;
  service: Services;
  from_date: string;
  to_date: string;
};

type ValidationSummary = {
  variant: "success" | "warning" | "danger" | "info";
  attempted: number;
  success: number;
  description: string;
};

function getValidationSummary(metadata: ImportMetadata): ValidationSummary {
  const attempted = metadata.attempted_count ?? 0;
  const success = metadata.success_count ?? 0;

  if (attempted === 0) {
    return {
      variant: "info",
      attempted,
      success,
      description: "No listens were processed.",
    };
  }

  if (success === 0) {
    return {
      variant: "danger",
      attempted,
      success,
      description: "None of the listens were imported.",
    };
  }

  if (success < attempted) {
    return {
      variant: "warning",
      attempted,
      success,
      description: "Some listens were rejected.",
    };
  }

  return {
    variant: "success",
    attempted,
    success,
    description: "All listens imported successfully.",
  };
}

function renderImport(
  im: Import,
  cancelImport: (event: React.SyntheticEvent, importToCancelId: number) => void,
  fetchImport: (importId: number) => Promise<any>
) {
  const validationSummary = getValidationSummary(im.metadata);
  const hasValidationData =
    (im.metadata.attempted_count ?? 0) > 0 ||
    (im.metadata.success_count ?? 0) > 0;
  const extraInfo = (
    <div>
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
          <dd className="col-8">{im.metadata.progress}</dd>
          <dt className="col-4">Requested on</dt>
          <dd className="col-8">{format(im.created, "PPp")}</dd>
          <dt className="col-4">Import #</dt>
          <dd className="col-8">{im.import_id}</dd>
          <dt className="col-4">File name</dt>
          <dd className="col-8">{im.metadata.filename}</dd>
          <dt className="col-4">Listens imported</dt>
          <dd className="col-8" data-testid="validation-counts-detail">
            {im.metadata.success_count ?? 0} /{" "}
            {im.metadata.attempted_count ?? 0}
          </dd>
          <dt className="col-4">Service</dt>
          <dd className="col-8">
            {Services[(im.service as unknown) as keyof typeof Services]}
          </dd>
          <dt className="col-4">Start date</dt>
          <dd className="col-8">
            {isValid(new Date(im.from_date)) &&
            new Date(im.from_date).getTime() !== 0
              ? format(new Date(im.from_date), "PPP")
              : "-"}
          </dd>
          <dt className="col-4">End date</dt>
          <dd className="col-8">
            {isValid(new Date(im.to_date)) ? format(im.to_date, "PPP") : "-"}
          </dd>
        </dl>
      </details>
    </div>
  );
  if (im.metadata.status === ImportStatus.complete) {
    const alertVariant = validationSummary.variant;
    return (
      <div
        key={im.import_id}
        className={`mt-4 alert alert-${alertVariant}`}
        role="alert"
      >
        <h4 className="alert-heading">Import completed!</h4>

        {hasValidationData && (
          <p className="mb-2" data-testid="validation-summary">
            Imported {validationSummary.success} / {validationSummary.attempted}
            &nbsp;listens. {validationSummary.description}
          </p>
        )}
        <p>
          <b>
            Note: the uploaded file(s) will be deleted automatically after the
            import
          </b>
        </p>
        {extraInfo}
      </div>
    );
  }
  if (im.metadata.status === ImportStatus.failed) {
    return (
      <div key={im.import_id} className="mt-4 alert alert-danger" role="alert">
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
    <div key={im.import_id} className="mt-4 alert alert-info" role="alert">
      <h4 className="alert-heading">
        Import in progress
        <br />
      </h4>
      <p className="text-primary">
        <FontAwesomeIcon icon={faArrowRightLong} />
        &nbsp;{im.metadata.progress}
        <button
          type="button"
          className="btn btn-sm btn-transparent"
          aria-label="Refresh"
          onClick={() => {
            fetchImport(im.import_id);
          }}
        >
          <FontAwesomeIcon icon={faRefresh} />
        </button>
      </p>
      <p>Feel free to close this page while we import your listens.</p>
      {hasValidationData && (
        <p className="mb-2">
          Imported {validationSummary.success} / {validationSummary.attempted}
          &nbsp;listens so far.
        </p>
      )}
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
  const { user_has_email: userHasEmail, pg_timezones, user_timezone } = data;

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const [loading, setLoading] = React.useState(false);
  const [imports, setImports] = React.useState<Array<Import>>([]);
  const [fileSelected, setFileSelected] = React.useState(false);
  const [selectedService, setSelectedService] = React.useState<
    keyof typeof Services
  >("spotify");

  const headers = useMemo((): Headers => {
    const obj = new Headers();
    obj.append("Content-Type", "application/json");
    if (currentUser?.auth_token) {
      obj.append("Authorization", `Token ${currentUser.auth_token}`);
    }
    return obj;
  }, [currentUser]);

  React.useEffect(() => {
    // Fetch the list of imports in progress in background tasks or finished
    async function getImportsInProgress() {
      try {
        const response = await fetch(
          `${APIService.APIBaseURI}/import-listens/list/`,
          {
            method: "GET",
            headers,
          }
        );
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText);
        }
        // Expecting an array of imports
        const results: Array<Import> = await response.json();
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
  }, [APIService.APIBaseURI, headers]);

  const fetchImport = React.useCallback(
    async function fetchImport(id: number) {
      setLoading(true);
      try {
        const nexImport = await APIService.getUserDataImportStatus(
          id,
          currentUser?.auth_token
        );
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
    [APIService, currentUser?.auth_token]
  );

  const hasAnImportInProgress =
    imports.findIndex(
      (imp) =>
        imp.metadata.status === ImportStatus.inProgress ||
        imp.metadata.status === ImportStatus.waiting
    ) !== -1;

  const createImport = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      if (event) event.preventDefault();
      try {
        const form = event.currentTarget;
        const formData = new FormData(form);

        if (!currentUser?.auth_token) {
          toast.error(
            <ToastMsg
              title="There was an error in authorization"
              message="No auth token was provided!"
            />
          );
          return;
        }
        const response = await fetch(
          `${APIService.APIBaseURI}/import-listens/`,
          {
            method: "POST",
            headers: {
              Authorization: `Token ${currentUser?.auth_token}`,
            },
            body: formData,
          }
        );

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
    [APIService.APIBaseURI, currentUser?.auth_token]
  );

  const cancelImport = React.useCallback(
    async (event: React.SyntheticEvent, importToCancelId: number) => {
      event.preventDefault();
      try {
        const response = await fetch(
          `${APIService.APIBaseURI}/import-listens/cancel/${importToCancelId}`,
          {
            method: "POST",
            headers,
          }
        );

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
    [APIService.APIBaseURI, headers]
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
      <ReactTooltip id="info-tooltip" place="top">
        Fun Fact: The term <strong>scrobble</strong> is a trademarked term by
        Last.fm, and we cannot use it.
        <br />
        Instead, we use the term <strong>listen</strong> for our data.
      </ReactTooltip>
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
      <p>
        We currently support export files from: <b>{humanReadableServices}</b>.
      </p>
      <div className="alert alert-warning fade show" role="alert">
        <p>
          For <b>{zipServices.join(", ")}</b>: please upload the complete{" "}
          <mark>.zip</mark> archive as received, without extracting the files
          within.
          <br />
          For <b>{nonZipServices.join(", ")}</b>: please upload single files
          directly (
          <mark>
            {nonZipServices.map((s) => acceptedFileTypes[s]).join(", ")}
          </mark>{" "}
          respectively).
        </p>
      </div>
      <div className="card">
        <div className="card-body">
          <form onSubmit={createImport}>
            <div className="flex flex-wrap" style={{ gap: "1em" }}>
              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="service">
                  Select Service:
                </label>
                <select
                  className="form-select"
                  id="service"
                  name="service"
                  required
                  value={selectedService}
                  onChange={(e) =>
                    setSelectedService(
                      e.currentTarget.value as keyof typeof Services
                    )
                  }
                >
                  {Object.entries(Services).map(([key, value], idx) => (
                    <option value={key} key={key}>
                      {value}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="file-upload">
                  Select your {acceptedFileTypes[Services[selectedService]]}{" "}
                  file:
                </label>
                <input
                  type="file"
                  id="file-upload"
                  className="form-control"
                  name="file"
                  accept={acceptedFileTypes[Services[selectedService]]}
                  required
                  onChange={(e) => setFileSelected(!!e.target.files?.length)}
                />
              </div>
            </div>

            <details className="mt-3">
              <summary>
                <FontAwesomeIcon
                  icon={faChevronCircleRight}
                  size="sm"
                  className="summary-indicator"
                />
                Additional options
              </summary>
              <div className="flex flex-wrap mt-3" style={{ gap: "1em" }}>
                <div style={{ minWidth: "15em" }}>
                  <label className="form-label" htmlFor="timezone">
                    Timezone (optional):
                  </label>
                  <select
                    className="form-select"
                    id="timezone"
                    name="timezone"
                    defaultValue={user_timezone}
                    title="Timezone fallback for ambiguous timestamps"
                    disabled={selectedService !== "audioscrobbler"}
                  >
                    <option value="">
                      Use profile timezone ({user_timezone})
                    </option>
                    {pg_timezones.map(([name, offset]) => (
                      <option key={name} value={name}>
                        {name}
                        {offset ? ` (${offset})` : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ minWidth: "15em" }}>
                  <label className="form-label" htmlFor="start-datetime">
                    Start import from (optional):
                  </label>
                  <input
                    type="date"
                    id="start-datetime"
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
                    id="end-datetime"
                    className="form-control"
                    max={new Date().toISOString()}
                    name="to_date"
                    title="Date and time to end import at"
                  />
                </div>
              </div>
            </details>

            <div className="mt-4" style={{ minWidth: "15em" }}>
              <button
                type="submit"
                className="btn btn-success"
                style={{
                  padding: "1rem 2.5rem",
                }}
                disabled={hasAnImportInProgress || !fileSelected}
              >
                Import Listens
              </button>
            </div>
          </form>
        </div>
      </div>

      <section id="import-buttons">
        <Loader isLoading={loading} style={{ margin: "0 1em" }} />
        {imports &&
          imports.map((im) => renderImport(im, cancelImport, fetchImport))}
      </section>
    </>
  );
}
