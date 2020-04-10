/* eslint-disable */
// TODO: Make the code ESLint compliant

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react"; // jsx compiled to React.createElement
import _ from "lodash";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

const getSpotifyEmbedUriFromListen = (listen: any) : string | null => {
  const spotifyId = _.get(listen, "track_metadata.additional_info.spotify_id");
  if (typeof spotifyId !== "string") {
    return null;
  }
  const spotify_track = spotifyId.split("https://open.spotify.com/")[1];
  if (typeof spotify_track !== "string") {
    return null;
  }
  return spotifyId.replace(
    "https://open.spotify.com/",
    "https://open.spotify.com/embed/"
  );
}

const searchForSpotifyTrack = async (
  spotifyToken?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string
): Promise<any> => {
  if (!spotifyToken) {
    throw new Error(JSON.stringify({
      status: 403,
      message: "You need to connect to your Spotify account",
    }));
  }
  if (!trackName) {
    console.error(
      "searchForSpotifyTrack was not passed a trackName, cannot proceed"
    );
    return null;
  }
  const queryString = `q="${trackName}"
    ${artistName && ` artist:${artistName}`}
    ${releaseName && ` album:${releaseName}`}
    &type=track`;

  const response = await fetch(
    `https://api.spotify.com/v1/search?${encodeURI(queryString)}`,
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
  const tracks = _.get(responseBody, "tracks.items");
  if (tracks && tracks.length) {
    return tracks[0];
  }
  return null;
}

const getArtistLink = (listen: any) => {
  const artistName = _.get(listen, "track_metadata.artist_name");
  const firstArtist = _.first(
    _.get(listen, "track_metadata.additional_info.artist_mbids")
  );
  if (firstArtist) {
    return (
      <a href={`http://musicbrainz.org/artist/${firstArtist}`} target="_blank">
        {artistName}
      </a>
    );
  }
  return artistName;
}

// TODO: remove this "any" when a listen type has been defined.
const getTrackLink = (listen: any): JSX.Element | string => {
  const trackName = _.get(listen, "track_metadata.track_name");
  if (_.get(listen, "track_metadata.additional_info.recording_mbid")) {
    return (
      <a
        href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}
        target="_blank"
      >
        {trackName}
      </a>
    );
  }
  return trackName;
}

const getPlayButton = (listen: any, onClickFunction: () => void) => {
  return (
    <button
      title="Play"
      className="btn-link"
      onClick={onClickFunction.bind(listen)}
    >
      <FontAwesomeIcon size="2x" icon={faPlayCircle.iconName as IconProp} />
    </button>
  );
}

export {getSpotifyEmbedUriFromListen, searchForSpotifyTrack, getArtistLink, getTrackLink, getPlayButton};
