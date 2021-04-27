import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as _ from "lodash";
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

export { searchForSpotifyTrack, getArtistLink, getTrackLink, getPlayButton };
