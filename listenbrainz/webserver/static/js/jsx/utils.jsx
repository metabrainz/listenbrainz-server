import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import React from 'react'; // jsx compiled to React.createElement
import { faPlayCircle } from '@fortawesome/free-solid-svg-icons'

export function getSpotifyEmbedUriFromListen(listen){
	
	if( typeof _.get(listen,"track_metadata.additional_info.spotify_id") !== "string"){
		return null;
	}
	const spotifyId = listen.track_metadata.additional_info.spotify_id;
	const spotify_track = spotifyId.split('https://open.spotify.com/')[1];
	if(typeof spotify_track !== "string"){
		return null;
	}
	return  spotifyId.replace("https://open.spotify.com/","https://open.spotify.com/embed/");
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
  if (_.get(listen,"track_metadata.additional_info.spotify_id"))
  {
    return (
      <button title="Play" className="btn-link" onClick={onClickFunction.bind(listen)}>
        <FontAwesomeIcon size="2x" icon={faPlayCircle}/>
      </button>
    )
  }
  return null;
}
