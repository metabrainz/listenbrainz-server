import React from 'react'; // jsx compiled to React.createElement

export function getSpotifyEmbedUriFromListen(listen){
	
	if(!listen || !listen.track_metadata || !listen.track_metadata.additional_info ||
		typeof listen.track_metadata.additional_info.spotify_id !== "string"){
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
  if (listen.track_metadata.additional_info.artist_mbids && listen.track_metadata.additional_info.artist_mbids.length)
  {
    return (<a href={`http://musicbrainz.org/artist/${listen.track_metadata.additional_info.artist_mbids[0]}`}>
      {listen.track_metadata.artist_name}
    </a>);
  }
  return listen.track_metadata.artist_name
}

export function getTrackLink(listen) {
  if (listen.track_metadata.additional_info.recording_mbid)
  {
    return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}>
      {listen.track_metadata.track_name}
    </a>);
  }
  return listen.track_metadata.track_name;
}

export function getPlayButton(listen, onClickFunction) {
  if (listen.track_metadata.additional_info.spotify_id)
  {
    return (
      <button title="Play" className="btn-link" onClick={onClickFunction.bind(listen)}>
        <i className="fas fa-play-circle fa-2x"></i>
      </button>
    )
  }
  return null;
}