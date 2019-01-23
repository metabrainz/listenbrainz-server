'use strict';

class SpotifyPlayer extends React.Component {

	_spotifyPlayer;
	_accessToken; 

	constructor(props) {
		super(props);
		this.state = { 
			currentSpotifyTrack: null,
			currentListen: null,
		};
		this._accessToken = props.spotify_access_token;
		this.playNextTrack = this.playNextTrack.bind(this);
		window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer.bind(this);
	}
 
	
	play_spotify_id(spotify_id){
		if(typeof spotify_id !== "string"){
			return;
		}
		const spotify_track = spotify_id.split('https://open.spotify.com/')[1];
		if(typeof spotify_track !== "string"){
			return;
		}
		const spotify_uri = "spotify:" + spotify_track.replace("/",":");
		this.play_spotify_uri(spotify_uri);
	}
	
	play_spotify_uri(spotify_uri){
		if(!this._spotifyPlayer) {
			console.error("Spotify player not initialized");
			return;
		}
		fetch(`https://api.spotify.com/v1/me/player/play?device_id=${this._spotifyPlayer._options.id}`, {
		method: 'PUT',
		body: JSON.stringify({ uris: [spotify_uri] }),
		headers: {
			'Content-Type': 'application/json',
			'Authorization': `Bearer ${this._accessToken}`
		},
	});
};

play_listen(listen){
	if(listen.track_metadata.additional_info.spotify_id){
		this.play_spotify_id(listen.track_metadata.additional_info.spotify_id);
		this.setState({currentListen: listen});
	}
};
isCurrentListen(element) {
  return element.listened_at === this.state.currentListen.listened_at;
}
playNextTrack(){
	if(this.props.nextListens.length === 0){
		console.log("No listens, maybe wait some?");
		this.setState({currentListen: null});
		return;
	}
	
	const currentListenIndex = this.props.nextListens.findIndex(this.isCurrentListen.bind(this));
	let nextListen;
	if(this.props.direction === "up"){
		nextListen = this.props.nextListens[currentListenIndex-1];
	} else{
		nextListen = this.props.nextListens[currentListenIndex+1];
	}
	if(!nextListen){
		console.log("No more listens, maybe wait some?");
		this.setState({currentListen: null});
		return;
	}
	this.play_listen(nextListen);
	this.setState({currentListen: nextListen});
}

connectSpotifyPlayer() {
	if(!this._accessToken){
		console.error("No spotify acces_token");
		return;
	}
	this._spotifyPlayer = new window.Spotify.Player({
		name: 'ListenBrainz Player',
		getOAuthToken: callback => {
			callback(this._accessToken);
		},
		volume: 1
	});
	
	// Error handling
	this._spotifyPlayer.on('initialization_error', console.error);
	this._spotifyPlayer.on('authentication_error', console.error);
	this._spotifyPlayer.on('account_error', console.error);
	this._spotifyPlayer.on('playback_error', console.error);
	
	
	this._spotifyPlayer.addListener('ready', ({ device_id }) => {
		console.log('Spotify player connected with Device ID', device_id);
	});
	
	this._spotifyPlayer.addListener('player_state_changed', this.handlePlayerStateChanged.bind(this));
	
	this._spotifyPlayer.connect().then(success => {
			if (success) {
				console.log('The Web Playback SDK successfully connected to Spotify!');
			}
			else {
				console.log('Could not connect Web Playback SDK');
			}
		});
	}
	handlePlayerStateChanged({
		paused,
		position,
		duration,
		track_window: { current_track }
	}) {
		console.log('Currently Playing', current_track);
		console.log('Position in Song', position);
		console.log('Duration of Song', duration);
		console.log('Player paused?', paused);
		// console.log("currentListen is same as nextListen?", currentListen.recording_msid === nextListens[0].recording_msid);
		
		// How do we accurately detect the end of a song?
		if(position === 0 && paused === true
			// currentListen && currentListen.recording_msid === nextListens[0] && nextListens[0].recording_msid )
			) {
				// Track finished, play next track
				console.log("Detected Spotify end of track, playing next track")
				this.playNextTrack();
				return;
			}
			this.setState({currentSpotifyTrack: current_track});
	}
		
		
	
	render(){
		return (
			<div className="col-md-4">
			
			<button className="btn btn-sm btn-default" onClick={this.playNextTrack}><span className="fa fa-forward"></span> Next</button>
			<h3>Currently playing:</h3>
			<div>
			{this.state.currentSpotifyTrack && 
				`${this.state.currentSpotifyTrack.name} – ${this.state.currentSpotifyTrack.artists.map(artist => artist.name).join(', ')}`
			}
			{this.state.currentListen && this.state.currentListen.user_name &&
				`from ${this.state.currentListen.user_name}'s listens`
			}
			</div>
			</div>
			);
		}
	}
	
	
	
	class RecentListens extends React.Component {
		constructor(props) {
			super(props);
			this.state = { listens: props.listens };
			// this.playListen = this.playListen.bind(this);
			this.spotifyPlayer = React.createRef();
		}
		
		playListen(listen){
			this.spotifyPlayer.current && this.spotifyPlayer.current.play_listen(listen);
		}
		
		render() {
			const getArtistLink = listen => {
				if(listen.track_metadata.additional_info.artist_mbids && listen.track_metadata.additional_info.artist_mbids.length){
					return (<a href={`http://musicbrainz.org/artist/${listen.track_metadata.additional_info.artist_mbids[0]}`}>
					{listen.track_metadata.artist_name}
					</a>);
				}
				return listen.track_metadata.artist_name
			}
			
			const getTrackLink = listen => {
				if(listen.track_metadata.additional_info.recording_mbid) {
					return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}>
					{ listen.track_metadata.track_name }
					</a>);
				}
				return listen.track_metadata.track_name;
			}
			
			
			return (
				<div>
				
				<div className="row">
				<div className="col-md-8">
				<h3> Statistics </h3>
				<table className="table table-border table-condensed table-striped">
				<tbody>
				{this.props.listen_count && 
					<tr>
					<td>Listen count</td>
					<td>{ this.props.listen_count }</td>
					</tr>
				}
				{ this.props.artist_count &&
					<tr>
					<td>Artist count</td>
					<td>{ this.props.artist_count }</td>
					</tr>
				}
				</tbody>
				</table>
				</div>
				</div>
				<div className="row">
				<h3>Recent listens</h3>
				<div className="col-md-8">
				
				{ !this.state.listens.length ?
					<p className="lead" style="text-align: center;">No listens :/</p> :
					
					<div >
					<table className="table table-condensed table-striped">
					<thead>
					<tr>
					<th>artist</th>
					<th>track</th>
					<th>time</th>
					</tr>
					</thead>
					<tbody>
					{this.state.listens.map((listen,index) => {
						if (listen.playing_now) {
							return (
								<tr id="playing_now" key={index}>
								<td>{ listen.track_metadata.artist_name }</td>
								<td>{ listen.track_metadata.track_name }</td>
								<td><span className="glyphicon glyphicon-play" aria-hidden="true"></span> Playing now</td>
								</tr>
								)
							} else {
								return (
									<tr key={index}>
									<td>
									{getArtistLink(listen)}
									</td>
									<td>
									{listen.track_metadata.additional_info.spotify_id &&
										<button className="btn btn-default btn-sm" onClick={this.playListen.bind(this,listen)}>
										<span className="fab fa-spotify"></span> Play
										</button>
									} {getTrackLink(listen)}
									</td>
									<td><abbr className="timeago" title={listen.listened_at_iso}>{ $.timeago(listen.listened_at_iso) }</abbr></td>
									</tr>
									)
								}
							})
						}
						
						</tbody>
						</table>
						
						<ul className="pager">
						<li className="previous" disabled={!this.props.previous_listen_ts}>
						<a href={`${this.props.profile_url}?min_ts=${this.props.previous_listen_ts}`}>&larr; Previous</a>
						</li>
						<li className="next" disabled={!this.props.next_listen_ts}>
						<a href={`${this.props.profile_url}?max_ts=${this.props.next_listen_ts}`}>Next &rarr;</a>
						</li>
						</ul>
						</div>
						
						
					}
					</div>
					<SpotifyPlayer
						ref={this.spotifyPlayer}
						nextListens={this.state.listens}
						direction="down"
						spotify_access_token= {this.props.spotify_access_token}
						{...this.props}/>
					</div>
					</div>
					);
				}
			}
			
			let domContainer = document.querySelector('#react-listens');
			let propsElement = document.getElementById('react-props');
			let reactProps;
			try{
				reactProps = JSON.parse(propsElement.innerHTML);
				console.log("props",reactProps);
			}
			catch(err){
				console.error("Error parsing props:", err);
			}
			ReactDOM.render(<RecentListens {...reactProps}/>, domContainer);
			
			
			
			