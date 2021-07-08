import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as _ from "lodash";
import * as timeago from "time-ago";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";

import { IconProp } from "@fortawesome/fontawesome-svg-core";

const searchForSpotifyTrack = async (
  spotifyToken?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string
): Promise<SpotifyTrack | null> => {
  if (!spotifyToken) {
    throw new Error(
      JSON.stringify({
        status: 403,
        message: "You need to connect to your Spotify account",
      })
    );
  }
  if (!trackName) {
    // search for track was not provided a track name, cannot proceed
    return null;
  }
  let queryString = `type=track&q=track:${encodeURIComponent(trackName)}`;
  if (artistName) {
    queryString += ` artist:${encodeURIComponent(artistName)}`;
  }
  if (releaseName) {
    queryString += ` album:${encodeURIComponent(releaseName)}`;
  }

  const response = await fetch(
    `https://api.spotify.com/v1/search?${queryString}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${spotifyToken}`,
      },
    }
  );
  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  // Valid response
  const tracks: SpotifyTrack[] = _.get(responseBody, "tracks.items");
  if (tracks && tracks.length) {
    return tracks[0];
  }
  return null;
};

const searchForYoutubeTrack = async (
  apiKey?: string,
  accessToken?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string,
  refreshToken?: () => Promise<string>,
  onAccountError?: () => void
): Promise<Array<string> | null> => {
  if (!apiKey) return null;
  if (!accessToken) return null;
  let query = trackName;
  if (artistName) {
    query += ` ${artistName}`;
  }
  // Considering we cannot tell the Youtube API that this should match only an album title,
  // results are paradoxically sometimes worse if we add it to the query (YT will find random matches for album title words)
  // if (releaseName) {
  //   query += ` ${releaseName}`;
  // }
  const response = await fetch(
    `https://youtube.googleapis.com/youtube/v3/search?part=snippet&q=${query}&videoEmbeddable=true&type=video&key=${apiKey}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (response.status === 401) {
    if (refreshToken) {
      try {
        const newAccessToken = await refreshToken();
        return searchForYoutubeTrack(
          apiKey,
          newAccessToken,
          trackName,
          artistName,
          releaseName,
          undefined
        );
      } catch (error) {
        // Run onAccountError if we can't refresh the token
        if (_.isFunction(onAccountError)) {
          onAccountError();
        }
      }
    }
    // Run onAccountError if we already tried refreshing the token but still getting 401
    if (_.isFunction(onAccountError)) {
      onAccountError();
    }
  }

  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  const tracks: Array<any> = _.get(responseBody, "items");
  const videoIds = tracks.map((track) => track.id.videoId);
  if (videoIds.length) return videoIds;
  return null;
};

const getArtistLink = (listen: Listen) => {
  const artistName = _.get(listen, "track_metadata.artist_name");
  const firstArtist = _.first(
    _.get(listen, "track_metadata.additional_info.artist_mbids")
  );
  if (firstArtist) {
    return (
      <a
        href={`http://musicbrainz.org/artist/${firstArtist}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {artistName}
      </a>
    );
  }
  return artistName;
};

const getTrackLink = (listen: Listen): JSX.Element | string => {
  const trackName = _.get(listen, "track_metadata.track_name");
  if (_.get(listen, "track_metadata.additional_info.recording_mbid")) {
    return (
      <a
        href={`https://musicbrainz.org/recording/${listen.track_metadata.additional_info?.recording_mbid}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {trackName}
      </a>
    );
  }
  return trackName;
};

const getPlayButton = (listen: any, onClickFunction: () => void) => {
  /* es-lint */
  return (
    <button
      title="Play"
      className="btn-link"
      onClick={onClickFunction.bind(listen)}
      type="button"
    >
      <FontAwesomeIcon size="2x" icon={faPlayCircle as IconProp} />
    </button>
  );
};

const formatWSMessageToListen = (wsMsg: any): Listen | null => {
  const json = wsMsg;
  try {
    // The websocket message received may not contain the expected track_metadata and listened_at fields.
    // Therefore, we look for their alias as well.
    if (!("track_metadata" in json)) {
      if ("data" in json) {
        json.track_metadata = json.data;
        delete json.data;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find track_metadata and data in following json: ",
          json
        );
        return null;
      }
    }
    if (!("listened_at" in json)) {
      if ("timestamp" in json) {
        json.listened_at = json.timestamp;
        delete json.timestamp;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find listened_at and timestamp in following json: ",
          json
        );
        return null;
      }
    }
    // The websocket message received contains the recording_msid as a top level key.
    // Therefore, we need to shift it json.track_metadata.additional_info.
    if (!_.has(json, "track_metadata.additional_info.recording_msid")) {
      if ("recording_msid" in json) {
        _.merge(json, {
          track_metadata: {
            additional_info: { recording_msid: json.recording_msid },
          },
        });
        delete json.recording_msid;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find recording_msid in following json: ",
          json
        );
        return null;
      }
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error);
    return null;
  }

  // The websocket message received contain some keys which are are either duplicates or are not required in the frontend.
  // Ideally this should be handled server-side and this will probably be fixed with protobuf move.
  return json as Listen;
};

// recieves or unix epoch timestamp int or ISO datetime string
const preciseTimestamp = (
  listened_at: number | string,
  displaySetting?: "timeAgo" | "includeYear" | "excludeYear"
): string => {
  const listenDate: Date = new Date(listened_at);
  let display = displaySetting;

  // invalid date
  if (Number.isNaN(listenDate.getTime())) {
    return String(listened_at);
  }

  // determine which display setting based on time difference to use if no argument was provided
  if (!display) {
    const msDifference = new Date().getTime() - listenDate.getTime();
    // over one year old : show with year
    if (msDifference / (1000 * 3600 * 24 * 365) > 1) {
      display = "includeYear";
    }
    // one year to yesterday : show without year
    else if (msDifference / (1000 * 3600 * 24 * 1) > 1) {
      display = "excludeYear";
    }
    // today : format using timeago
    else display = "timeAgo";
  }

  switch (display) {
    case "includeYear":
      return `${listenDate.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })}`;
    case "excludeYear":
      return `${listenDate.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })}`;
    default:
      return `${timeago.ago(listened_at)}`;
  }
};

/** Loads a script asynchronouhsly into the HTML page */
export function loadScriptAsync(document: any, scriptSrc: string): void {
  const el = document.createElement("script");
  const container = document.head || document.body;
  el.type = "text/javascript";
  el.async = true;
  el.src = scriptSrc;
  container.appendChild(el);
}

const createAlert = (
  type: AlertType,
  title: string,
  message: string | JSX.Element
): Alert => {
  return {
    id: new Date().getTime(),
    type,
    headline: title,
    message,
  };
};

interface GlobalProps {
  api_url: string;
  sentry_dsn: string;
  current_user: ListenBrainzUser;
  spotify?: SpotifyUser;
  youtube?: YoutubeUser;
}

const getPageProps = (): {
  domContainer: HTMLElement;
  reactProps: Record<string, any>;
  globalReactProps: GlobalProps;
  optionalAlerts: Alert[];
} => {
  let domContainer = document.getElementById("react-container");
  const propsElement = document.getElementById("page-react-props");
  const globalPropsElement = document.getElementById("global-react-props");
  let reactProps = {};
  let globalReactProps = {} as GlobalProps;
  const optionalAlerts = [];
  if (!domContainer) {
    // Ensure there is a container for React rendering
    // We should always have on on the page already, but displaying errors to the user relies on there being one
    domContainer = document.createElement("div");
    domContainer.id = "react-container";
    const container = document.getElementsByClassName("wrapper");
    container[0].appendChild(domContainer);
  }
  try {
    // Global props *cannot* be empty
    if (globalPropsElement?.innerHTML) {
      globalReactProps = JSON.parse(globalPropsElement.innerHTML);
    } else {
      throw new Error("No global props element found on the page");
    }
    // Page props can be empty
    if (propsElement?.innerHTML) {
      reactProps = JSON.parse(propsElement!.innerHTML);
    }
  } catch (err) {
    // Show error to the user and ask to reload page
    // eslint-disable-next-line no-console
    console.error(err);
    const errorMessage = `Please refresh the page.
	If the problem persists, please contact us.
	Reason: ${err}`;
    const newAlert = createAlert(
      "danger",
      "Error loading the page",
      errorMessage
    );
    optionalAlerts.push(newAlert);
  }
  return { domContainer, reactProps, globalReactProps, optionalAlerts };
};

export {
  searchForSpotifyTrack,
  getArtistLink,
  getTrackLink,
  getPlayButton,
  formatWSMessageToListen,
  preciseTimestamp,
  getPageProps,
  searchForYoutubeTrack,
  createAlert,
};
