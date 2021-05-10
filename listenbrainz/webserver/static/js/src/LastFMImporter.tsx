import * as ReactDOM from "react-dom";
import * as React from "react";
import * as Sentry from "@sentry/react";
import { faSpinner, faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import APIService from "./APIService";
import Scrobble from "./Scrobble";
import LastFMImporterModal from "./LastFMImporterModal";

export const LASTFM_RETRIES = 3;

export type ImporterProps = {
  user: {
    id?: string;
    name: string;
    auth_token: string;
  };
  profileUrl?: string;
  apiUrl?: string;
  lastfmApiUrl: string;
  lastfmApiKey: string;
};

export type ImporterState = {
  show: boolean;
  canClose: boolean;
  lastfmUsername: string;
  msg?: React.ReactElement;
};

export default class LastFmImporter extends React.Component<
  ImporterProps,
  ImporterState
> {
  static encodeScrobbles(scrobbles: LastFmScrobblePage): any {
    const rawScrobbles = scrobbles.recenttracks.track;
    const parsedScrobbles = LastFmImporter.map((rawScrobble: any) => {
      const scrobble = new Scrobble(rawScrobble);
      return scrobble.asJSONSerializable();
    }, rawScrobbles);
    return parsedScrobbles;
  }

  static map(applicable: (collection: any) => Listen, collection: any) {
    const newCollection = [];
    for (let i = 0; i < collection.length; i += 1) {
      const result = applicable(collection[i]);
      if (result.listened_at > 0) {
        // If the 'listened_at' attribute is -1 then either the listen is invalid or the
        // listen is currently playing. In both cases we need to skip the submission.
        newCollection.push(result);
      }
    }
    return newCollection;
  }

  APIService: APIService;
  private lastfmURL: string;
  private lastfmKey: string;

  private userName: string;
  private userToken: string;

  private page = 1;
  private totalPages = 0;

  private playCount = -1; // the number of scrobbles reported by Last.FM
  private countReceived = 0; // number of scrobbles the Last.FM API sends us, this can be diff from playCount

  private latestImportTime = 0; // the latest timestamp that we've imported earlier
  private maxTimestampForImport = 0; // the latest listen found in this import
  private lastImportedString = ""; // date formatted string of first song on payload's timestamp
  private incrementalImport = false;

  private numCompleted = 0; // number of pages completed till now

  // Variables used to honor LB's rate limit
  private rlRemain = -1;
  private rlReset = -1;

  private rlOrigin = -1;

  constructor(props: ImporterProps) {
    super(props);

    this.state = {
      show: false,
      canClose: true,
      lastfmUsername: "",
      msg: undefined,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.lastfmURL = props.lastfmApiUrl;
    this.lastfmKey = props.lastfmApiKey;

    this.userName = props.user.name;
    this.userToken = props.user.auth_token || "";
  }

  async getTotalNumberOfScrobbles() {
    /*
     * Get the total play count reported by Last.FM for user
     */
    const { lastfmUsername } = this.state;
    const url = `${this.lastfmURL}?method=user.getinfo&user=${lastfmUsername}&api_key=${this.lastfmKey}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      const data = await response.json();
      if ("playcount" in data.user) {
        return Number(data.user.playcount);
      }
      return -1;
    } catch {
      this.updateModalAction(
        <p>An error occurred, please try again. :(</p>,
        true
      );
      const error = new Error();
      error.message = "Something went wrong";
      throw error;
    }
  }

  async getNumberOfPages() {
    /*
     * Get the total pages of data from last import
     */
    const { lastfmUsername } = this.state;

    const url = `${
      this.lastfmURL
    }?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${
      this.lastfmKey
    }&from=${this.latestImportTime + 1}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      const data = await response.json();
      if ("recenttracks" in data) {
        return Number(data.recenttracks["@attr"].totalPages);
      }
      return 0;
    } catch (error) {
      this.updateModalAction(
        <p>An error occurred, please try again. :(</p>,
        true
      );
      return -1;
    }
  }

  /*
   * @param {number} page - the page to fetch from Last.fm
   * @param {number} retries - number times to retry in case of errors other than 40x
   * Fetch page from Last.fm
   * @returns Returns an array of Listens if successful, null if it exceeds the max number of retries (consider that an error)
   * and undefined if we receive a 40X error for the page
   */
  async getPage(
    page: number,
    retries: number
  ): Promise<Array<Listen> | undefined> {
    const { lastfmUsername } = this.state;
    const timeout = 3000;

    const url = `${
      this.lastfmURL
    }?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${
      this.lastfmKey
    }&from=${this.latestImportTime + 1}&page=${page}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      if (response.ok) {
        const data = await response.json();
        // Set latest import time
        if ("date" in data.recenttracks.track[0]) {
          this.maxTimestampForImport = Math.max(
            data.recenttracks.track[0].date.uts,
            this.maxTimestampForImport
          );
        } else {
          this.maxTimestampForImport = Math.floor(Date.now() / 1000);
        }

        // Encode the page so that it can be submitted
        const payload = LastFmImporter.encodeScrobbles(data);
        this.countReceived += payload.length;
        return payload;
      }
      // Retry if we receive a 5xx server error
      if (/^5/.test(response.status.toString())) {
        throw new Error(`Status ${response.status}`);
      }
    } catch (err) {
      // Retry if there is a network error
      // eslint-disable-next-line no-console
      console.warn(`Error while fetching last.fm page ${page}:`, err);
      if (retries <= 0) {
        throw new Error(
          `Failed to fetch page ${page} from last.fm after ${LASTFM_RETRIES} retries.`
        );
      }
      // eslint-disable-next-line no-console
      console.warn(`Retrying in ${timeout / 1000}s, ${retries} retries left`);
      await new Promise((resolve) => setTimeout(resolve, timeout));
      // eslint-disable-next-line no-return-await
      return await this.getPage(page, retries - 1);
    }
    return undefined;
  }

  static getlastImportedString(listen: Listen) {
    // Retrieve first track's timestamp from payload and convert it into string for display
    const lastImportedDate = new Date(listen.listened_at * 1000);
    return lastImportedDate.toLocaleString("en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "numeric",
      hour12: true,
    });
  }

  getRateLimitDelay() {
    /* Get the amount of time we should wait according to LB rate limits before making a request to LB */
    let delay = 0;
    const current = new Date().getTime() / 1000;
    if (this.rlReset < 0 || current > this.rlOrigin + this.rlReset) {
      delay = 0;
    } else if (this.rlRemain > 0) {
      delay = Math.max(0, Math.ceil((this.rlReset * 1000) / this.rlRemain));
    } else {
      delay = Math.max(0, Math.ceil(this.rlReset * 1000));
    }
    return delay;
  }

  updateModalAction = (msg: React.ReactElement, canClose: boolean) => {
    this.setState({
      msg,
      canClose,
    });
  };

  toggleModal = () => {
    this.setState((prevState) => {
      return { show: !prevState.show };
    });
  };

  setClose = (canClose: boolean) => {
    this.setState({ canClose });
  };

  handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({ lastfmUsername: event.target.value });
  };

  handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    const { lastfmUsername } = this.state;
    this.toggleModal();
    event.preventDefault();
    this.startImport();
  };

  async submitPage(payload: Array<Listen>) {
    const delay = this.getRateLimitDelay();
    // Halt execution for some time
    await new Promise((resolve) => {
      setTimeout(resolve, delay);
    });

    const response = await this.APIService.submitListens(
      this.userToken,
      "import",
      payload
    );
    this.updateRateLimitParameters(response);
  }

  async importLoop() {
    while (this.page > 0) {
      // Fixing no-await-in-loop will require significant changes to the code, ignoring for now
      this.lastImportedString = "...";
      const payload = await this.getPage(this.page, LASTFM_RETRIES); // eslint-disable-line

      if (payload) {
        // Submit only if response is valid
        this.submitPage(payload);
        this.lastImportedString = LastFmImporter.getlastImportedString(
          payload[0]
        );
      }

      this.page -= 1;
      this.numCompleted += 1;

      // Update message
      const msg = (
        <p>
          <FontAwesomeIcon icon={faSpinner as IconProp} spin /> Sending page{" "}
          {this.numCompleted} of {this.totalPages} to ListenBrainz <br />
          <span style={{ fontSize: `${8}pt` }}>
            {this.incrementalImport && (
              <span>
                Note: This import will stop at the starting point of your last
                import. :)
                <br />
              </span>
            )}
            <span>
              Please don&apos;t close this page while this is running.
            </span>{" "}
            <br /> <br />
            <span> Latest import timestamp: {this.lastImportedString} </span>
          </span>
        </p>
      );
      this.setState({ msg });
    }
  }

  async startImport() {
    this.updateModalAction(<p>Your import from Last.fm is starting!</p>, false);
    this.latestImportTime = await this.APIService.getLatestImport(
      this.userName
    );
    this.incrementalImport = this.latestImportTime > 0;
    this.playCount = await this.getTotalNumberOfScrobbles();
    this.totalPages = await this.getNumberOfPages();
    this.page = this.totalPages; // Start from the last page so that oldest scrobbles are imported first

    let finalMsg: JSX.Element;
    const { profileUrl } = this.props;

    try {
      await this.importLoop(); // import pages
    } catch (err) {
      // import failed, show final message on unhandled exception / unrecoverable network error
      finalMsg = (
        <p>
          <FontAwesomeIcon icon={faTimes as IconProp} /> We were unable to
          import from LastFM, please try again.
          <br />
          If the problem persists please contact us.
          <br />
          {err.toString()}
          <br />
          <span style={{ fontSize: `${10}pt` }}>
            <a href={`${profileUrl}`}>
              Close and go to your ListenBrainz profile
            </a>
          </span>
        </p>
      );
      // eslint-disable-next-line no-console
      console.error(err);
      this.setState({ canClose: true, msg: finalMsg });
      return Promise.resolve(null);
    }

    // import was successful
    try {
      this.maxTimestampForImport = Math.max(
        Number(this.maxTimestampForImport),
        this.latestImportTime
      );
      this.APIService.setLatestImport(
        this.userToken,
        this.maxTimestampForImport
      );
    } catch {
      // console.warn("Error setting latest import timestamp, retrying in 3s");
      setTimeout(
        () =>
          this.APIService.setLatestImport(
            this.userToken,
            this.maxTimestampForImport
          ),
        3000
      );
    }
    finalMsg = (
      <p>
        <FontAwesomeIcon icon={faCheck as IconProp} />
        Import finished
        <br />
        <span style={{ fontSize: `${8}pt` }}>
          Successfully submitted {this.countReceived} listens to ListenBrainz
          <br />
        </span>
        {/* if the count received is different from the api count, show a message accordingly
         * also don't show this message if it's an incremental import, because countReceived
         * and playCount will be different by definition in incremental imports
         */}
        {!this.incrementalImport &&
          this.playCount !== -1 &&
          this.countReceived !== this.playCount && (
            <b>
              <span style={{ fontSize: `${10}pt` }} className="text-danger">
                The number submitted listens is different from the{" "}
                {this.playCount} that Last.fm reports due to an inconsistency in
                their API, sorry!
                <br />
              </span>
            </b>
          )}
        <span style={{ fontSize: `${8}pt` }}>
          Thank you for using ListenBrainz!
        </span>
        <br />
        <br />
        <span style={{ fontSize: `${10}pt` }}>
          <a href={`${profileUrl}`}>
            Close and go to your ListenBrainz profile
          </a>
        </span>
      </p>
    );
    this.setState({ canClose: true, msg: finalMsg });
    return Promise.resolve(null);
  }

  updateRateLimitParameters(response: Response) {
    /* Update the variables we use to honor LB's rate limits */
    this.rlRemain = Number(response.headers.get("X-RateLimit-Remaining"));
    this.rlReset = Number(response.headers.get("X-RateLimit-Reset-In"));
    this.rlOrigin = new Date().getTime() / 1000;
  }

  render() {
    const { show, canClose, lastfmUsername, msg } = this.state;
    return (
      <div className="Importer">
        <form onSubmit={this.handleSubmit}>
          <input
            type="text"
            onChange={this.handleChange}
            value={lastfmUsername}
            placeholder="Last.fm Username"
            size={30}
          />
          <input type="submit" value="Import Now!" disabled={!lastfmUsername} />
        </form>
        {show && (
          <LastFMImporterModal onClose={this.toggleModal} disable={!canClose}>
            <img
              src="/static/img/listenbrainz-logo.svg"
              height="75"
              className="img-responsive"
              alt=""
            />
            <br />
            <br />
            <div>{msg}</div>
            <br />
          </LastFMImporterModal>
        )}
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // Show error to the user and ask to reload page
  }
  const {
    user,
    profile_url,
    api_url,
    lastfm_api_url,
    lastfm_api_key,
    sentry_dsn,
  } = reactProps;

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  ReactDOM.render(
    <LastFmImporter
      user={user}
      profileUrl={profile_url}
      apiUrl={api_url}
      lastfmApiKey={lastfm_api_key}
      lastfmApiUrl={lastfm_api_url}
    />,
    domContainer
  );
});
