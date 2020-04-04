import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import React from 'react'; // jsx compiled to React.createElement
import { faPlayCircle } from '@fortawesome/free-solid-svg-icons'

export function getSpotifyEmbedUriFromListen(listen){
  let spotifyId = _.get(listen,"track_metadata.additional_info.spotify_id")
	if(typeof spotifyId !== "string"){
      return null;
	}
	const spotify_track = spotifyId.split('https://open.spotify.com/')[1];
	if(typeof spotify_track !== "string"){
		return null;
	}
	return  spotifyId.replace("https://open.spotify.com/","https://open.spotify.com/embed/");
}

export async function searchForSpotifyTrack(spotifyToken, trackName, artistName, releaseName) {
  if(!spotifyToken) {
    throw new Error({status:403,message: "You need to connect to your Spotify account"});
  }
  if(!trackName){
    console.error("searchForSpotifyTrack was not passed a trackName, cannot proceed");
    return null;
  }
  const queryString = `q="${trackName}"
    ${artistName &&  " artist:"+artistName}
    ${releaseName &&  " album:"+releaseName}
    &type=track`;
    
  const response = await fetch(`https://api.spotify.com/v1/search?${encodeURI(queryString)}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${spotifyToken}`
    },
  });
  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  // Valid response
  const tracks = _.get(responseBody,"tracks.items");
    if(tracks && tracks.length){
      return tracks[0];
    }
  return null;
}

export function getArtistLink(listen) {
  const artistName = _.get(listen,"track_metadata.artist_name");
  const firstArtist = _.first(_.get(listen,"track_metadata.additional_info.artist_mbids"));
  if (firstArtist)
  {
    return (<a href={`http://musicbrainz.org/artist/${firstArtist}`}
      target="_blank">
      {artistName}
    </a>);
  }
  return artistName;
}

export function getTrackLink(listen) {
  const trackName = _.get(listen,"track_metadata.track_name");
  if (_.get(listen,"track_metadata.additional_info.recording_mbid"))
  {
    return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}
      target="_blank">
      {trackName}
    </a>);
  }
  return trackName;
}

export function getPlayButton(listen, onClickFunction) {
  return (
    <button title="Play" className="btn-link" onClick={onClickFunction.bind(listen)}>
      <FontAwesomeIcon size="2x" icon={faPlayCircle}/>
    </button>
  )
}
