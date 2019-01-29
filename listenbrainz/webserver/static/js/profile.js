'use strict';

function getSpotifyEmbedUriFromListen(listen){
	
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

function getSpotifyUriFromListen(listen){
	
	if(!listen || !listen.track_metadata || !listen.track_metadata.additional_info ||
		typeof listen.track_metadata.additional_info.spotify_id !== "string"){
		return null;
	}
	const spotifyId = listen.track_metadata.additional_info.spotify_id;
	const spotify_track = spotifyId.split('https://open.spotify.com/')[1];
	if(typeof spotify_track !== "string"){
		return null;
	}
	return "spotify:" + spotify_track.replace("/",":");
}
function millisecondsToHumanReadable(milliseconds)
{
	var seconds = milliseconds/1000;
	var numyears = Math.floor(seconds / 31536000);
	var numdays = Math.floor((seconds % 31536000) / 86400); 
	var numhours = Math.floor(((seconds % 31536000) % 86400) / 3600);
	var numminutes = Math.floor((((seconds % 31536000) % 86400) % 3600) / 60);
	var numseconds = Math.floor((((seconds % 31536000) % 86400) % 3600) % 60);
	var string="";
	if(numyears) string += numyears + " y ";
	if(numdays) string += numdays + " d ";
	if(numhours) string += numhours + " h ";
	if(numminutes) string += numminutes + " m ";
	if(numseconds) string += numseconds + " s";

	return string;
}

function getArtistLink(listen) {
	if(listen.track_metadata.additional_info.artist_mbids && listen.track_metadata.additional_info.artist_mbids.length){
		return (<a href={`http://musicbrainz.org/artist/${listen.track_metadata.additional_info.artist_mbids[0]}`}>
		{listen.track_metadata.artist_name}
		</a>);
	}
	return listen.track_metadata.artist_name
}

function getTrackLink(listen) {
	if(listen.track_metadata.additional_info.recording_mbid) {
		return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}>
		{ listen.track_metadata.track_name }
		</a>);
	}
	return listen.track_metadata.track_name;
}

function getSpotifyPlayButton(listen, onClickFunction) {
	if(listen.track_metadata.additional_info.spotify_id) {
		return (
			<button className="btn btn-info btn-sm" onClick={onClickFunction.bind(listen)}>
				<span className="fab fa-spotify"></span> Play
			</button>
		)
	}
	return null;
}

class SpotifyPlayer extends React.Component {

	_spotifyPlayer;
	_accessToken; 

	constructor(props) {
		super(props);
		this.state = { 
			listens: props.listens,
			currentSpotifyTrack: null,
			playerPaused:true,
			errorMessage:null,
			direction: props.direction || "down"
		};
		this._accessToken = props.spotify_access_token;
		this.playNextTrack = this.playNextTrack.bind(this);
		this.playPreviousTrack = this.playPreviousTrack.bind(this);
		this.togglePlay = this.togglePlay.bind(this);
		this.toggleDirection = this.toggleDirection.bind(this);
		this.handlePlayerStateChanged = this.handlePlayerStateChanged.bind(this);
		this.handleError = this.handleError.bind(this);
		this.isCurrentListen = this.isCurrentListen.bind(this);
		this.getAlbumArt = this.getAlbumArt.bind(this);
		window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer.bind(this);
	}
	
	play_spotify_uri(spotify_uri){
		if(!this._spotifyPlayer) {
			const error ="Spotify player not initialized. Please refresh the page";
			this.setState({errorMessage:error});
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
		this.play_spotify_uri(getSpotifyUriFromListen(listen));
		this.props.onCurrentListenChange(listen);
	}
};
isCurrentListen(element) {
	return this.props.currentListen
		&& element.listened_at
		&& element.listened_at === this.props.currentListen.listened_at;
}
playPreviousTrack(){
	this.playNextTrack(true);
}
playNextTrack(invert){
	if(this.state.listens.length === 0){
		const error = "No Spotify listens to play. Maybe refresh the page?";
		console.error(error);
		this.setState({errorMessage:error});

		return;
	}
	
	const currentListenIndex = this.state.listens.findIndex(this.isCurrentListen);
	let nextListen;
	if((this.state.direction === "up" && invert !== true) || invert === true){
		nextListen = this.state.listens[currentListenIndex-1];
	} else {
		nextListen = this.state.listens[currentListenIndex+1];
	}
	if(!nextListen){
		const error = "No more listens, maybe wait some?";
		console.error(error);
		this.setState({errorMessage:error});
		return;
	}
	this.play_listen(nextListen);
	this.setState({errorMessage:null});
}
handleError(error){
	console.error(error);
	error = error.message ? error.message : error;
	this.setState({errorMessage: error});
}

async togglePlay(){
	await this._spotifyPlayer.togglePlay();
}

toggleDirection(){
	this.setState(prevState =>{
		const direction = prevState.direction === "down"? "up" : "down";
		return {direction: direction }
	});
}

connectSpotifyPlayer() {
	if(!this._accessToken){
		console.error("No spotify acces_token");
		const noTokenErrorMessage = <span>No Spotify access token. Please try to <a href="/profile/connect-spotify">link your account</a> and refresh this page</span>;
		this.handleError(noTokenErrorMessage);
		return;
	}
	this._spotifyPlayer = new window.Spotify.Player({
		name: 'ListenBrainz Player',
		getOAuthToken: callback => {
			callback(this._accessToken);
		},
		volume: 0.7 // Careful with this, now…
	});

	// Error handling
	const authErrorMessage = <span>Spotify authentication error. Please try to refresh the page or <a href="/profile/connect-spotify">relink your Spotify account</a></span>
	this._spotifyPlayer.on('initialization_error', this.handleError);
	this._spotifyPlayer.on('authentication_error', error => this.handleError(authErrorMessage));
	this._spotifyPlayer.on('account_error', this.handleError);
	this._spotifyPlayer.on('playback_error', this.handleError);
	
	
	this._spotifyPlayer.addListener('ready', ({ device_id }) => {
		console.log('Spotify player connected with Device ID', device_id);
	});
	
	this._spotifyPlayer.addListener('player_state_changed', this.handlePlayerStateChanged);
	
	this._spotifyPlayer.connect().then(success => {
			if (success) {
				console.log('The Web Playback SDK successfully connected to Spotify!');
			}
			else {
				this.handleError('Could not connect Web Playback SDK');
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
		// console.log("currentListen is same as nextListen?", currentListen.recording_msid === listens[0].recording_msid);
		// How do we accurately detect the end of a song?
		if(position === 0 && paused === true
			// currentListen && currentListen.recording_msid === listens[0] && listens[0].recording_msid )
			) {
				// Track finished, play next track
				console.log("Detected Spotify end of track, playing next track")
				this.playNextTrack();
				return;
			}
			this.setState({
				currentSpotifyTrack: current_track,
				playerPaused: paused,
				errorMessage: null
			});
	}
		
	getAlbumArt(){
		const track = this.state.currentSpotifyTrack;
		if (!track || !track.album || !Array.isArray(track.album.images)){
			return null
		}
		const sortedImages = track.album.images.sort((a,b)=>a.height > b.height ? -1 :1);
		return sortedImages[0] &&
		<div className="img-responsive" className="thumbnail"><img src={sortedImages[0].url} style={{width: "100%"}}/></div>;
	}
	
	render(){
		const playerButtonStyle = {width: '24%'};
		return (
			<div>
				<div className="btn-group" role="group" aria-label="Playback control" style={{witdh: '100%'}}>

					<button className="btn btn-default"
						onClick={this.playPreviousTrack}
						style={playerButtonStyle}>
						<span className="fa fa-backward"></span> Prev
					</button>

					<button className="btn btn-default"
						onClick={this.togglePlay}
						style={playerButtonStyle}>
						<span className={`${this.state.playerPaused ? 'hidden' : ''}`}>
							<span className="fa fa-pause"></span>
						</span>
						<span className={`${!this.state.playerPaused ? 'hidden' : ''}`}>
							<span className="fa fa-play"></span>
						</span>
						&nbsp;&nbsp;
						{!this.state.playerPaused ? 'Pause' : 'Play'}
					</button>

					<button className="btn btn-default"
						onClick={this.toggleDirection}
						style={playerButtonStyle}>
							{this.state.direction}
							&nbsp;&nbsp;
							<span className={`${this.state.direction === 'up' ? 'hidden' : ''}`}>
								<span className="fa fa-angle-double-down"></span>
							</span>
							<span className={`${this.state.direction === 'down' ? 'hidden' : ''}`}>
								<span className="fa fa-angle-double-up"></span>
							</span>
					</button>

					<button className="btn btn-default"
						onClick={this.playNextTrack}
						style={playerButtonStyle}>
						Next <span className="fa fa-forward"></span>
					</button>

				</div>
				
				{this.state.errorMessage && 
					<div className="alert alert-danger" role="alert">
						{this.state.errorMessage}
					</div>
				}
				{this.state.currentSpotifyTrack && 
					<div>
						<h4>Currently playing:</h4>
						<h3 style={{borderBottom: "1px solid lightgrey"}}>
							{this.state.currentSpotifyTrack.name}
							{this.state.currentSpotifyTrack.duration_ms &&
								<span className="small"> — {millisecondsToHumanReadable(this.state.currentSpotifyTrack.duration_ms)}</span>
							}
						</h3>
						<p>{this.state.currentSpotifyTrack.artists.map(artist => artist.name).join(', ')}</p>
						<div>{this.getAlbumArt()}</div>
					</div>
				}
				{this.props.currentListen && this.props.currentListen.user_name &&
					<div>from {this.props.currentListen.user_name}'s listens</div>
				}
			</div>
			);
		}
	}
	
	
	
	class RecentListens extends React.Component {
		
		spotifyListens = [];
		constructor(props) {
			super(props);
			this.state = {
				listens: props.listens || [],
				currentListen : null,
				mode: props.mode === "follow" ? "follow" : "listens",
				playingNowByUser: {}
			};
			this.isCurrentListen = this.isCurrentListen.bind(this);
			this.handleCurrentListenChange = this.handleCurrentListenChange.bind(this);
			this.playListen = this.playListen.bind(this);
			this.spotifyPlayer = React.createRef();
			window.handleIncomingListen = this.receiveNewListen.bind(this);
			window.handleIncomingPlayingNow = this.receiveNewPlayingNow.bind(this);
		}
		
		playListen(listen){
			if(this.spotifyPlayer.current){
				this.spotifyPlayer.current.play_listen(listen);
				return;
			} else {
				// For fallback embedded player
				this.setState({currentListen:listen});
				return;
			}
		}

		receiveNewListen(newListen){
			try {
				newListen = JSON.parse(newListen);
			} catch (error) {
				console.error(error);
			}
			console.log(typeof newListen, newListen);
			this.setState(prevState =>{
				return { listens: [newListen].concat(prevState.listens)}
			})
		}
		receiveNewPlayingNow(newPlayingNow){
			try {
				newPlayingNow = JSON.parse(newPlayingNow);
			} catch (error) {
				console.error(error);
			}
			newPlayingNow.playing_now = true;

			this.setState(prevState =>{
				if(prevState.mode === "follow"){
					const userName = newPlayingNow.user_name;
					return {playingNowByUser: Object.assign(
						{},
						prevState.playingNowByUser,
						{[userName]:newPlayingNow}
						)
					}
				}
				const indexOfPreviousPlayingNow = prevState.listens.findIndex(listen => listen.playing_now);
				prevState.listens.splice(indexOfPreviousPlayingNow, 1);
				return { listens: [newPlayingNow].concat(prevState.listens)}
			})
		}
		
		handleCurrentListenChange(listen){
			this.setState({currentListen:listen});
		}
		isCurrentListen(listen){
			return this.state.currentListen && this.state.currentListen.listened_at === listen.listened_at;
		}
		handleFollowUserListChange(users){
			if(!Array.isArray(users)){
				console.error("Expected array in handleFollowUserListChange, got", typeof users);
				return;
			}
			if(typeof window.emitFollowUsersList !== "function"){
				console.error("window.emitFollowUsersList is not a function, can't emit follow users list");
				return;
			}
			window.emitFollowUsersList(users);
		}
		
		render() {
			
			const spotifyListens = this.state.listens.filter(listen => listen.track_metadata
					&& listen.track_metadata.additional_info
					&& listen.track_metadata.additional_info.listening_from === "spotify"
			);

			const getSpotifyEmbedSrc = () => {
				if(this.state.currentListen) {
					return getSpotifyEmbedUriFromListen(this.state.currentListen);
				} else if(spotifyListens.length){
					console.log(spotifyListens[0]);
					return getSpotifyEmbedUriFromListen(spotifyListens[0]);
				}
				return null
			};

			return (
				<div>
					{this.state.mode === "listens" && <div className="row">
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
					}
					{this.state.mode === "follow" &&
						<FollowUsers onUserListChange={this.handleFollowUserListChange}
						initialList={this.props.follow_list} playListen={this.playListen.bind(this)}
						playingNow={this.state.playingNowByUser}/>
					}
					<div className="row">
					<div className="col-md-8">
					<h3>{this.state.mode === "listens" ? "Recent listens" : "Playlist"}</h3>
					
					{ !this.state.listens.length ?
						<p className="lead" className="text-center">No listens :/</p> :
						<div>
							<table className="table table-condensed table-striped">
							<thead>
							<tr>
							<th>Artist</th>
							<th>Track</th>
							<th>Time</th>
							{this.state.mode === "follow" && <th>User</th>}
							<th>Play</th>
							</tr>
							</thead>
							<tbody>
							{this.state.listens
								.sort((a,b)=> a.playing_now ? -1 : b.playing_now ? 1 : 0) 
								.map((listen,index) => {
									if (listen.playing_now) {
										return (
											<tr id="playing_now" key='playing_now'>
											<td>{getArtistLink(listen)}</td>
											<td>{getTrackLink(listen)}</td>
											<td><span className="fab fa-spotify" aria-hidden="true"></span> Playing now</td>
											{this.state.mode === "follow" && <td>{listen.user_name}</td>}
											<td>{getSpotifyPlayButton(listen,this.playListen)}</td>
											</tr>
											)
										} else {
											return (
												<tr key={index} className={this.isCurrentListen(listen) ? 'info' : ''}>
												<td>{getArtistLink(listen)}</td>
												<td>{getTrackLink(listen)}</td>
												<td><abbr className="timeago" title={listen.listened_at_iso}>{ listen.listened_at_iso ? $.timeago(listen.listened_at_iso) : $.timeago(listen.listened_at*1000) }</abbr></td>
												{this.state.mode === "follow" && <td>{listen.user_name}</td>}
												<td>{getSpotifyPlayButton(listen,this.playListen)}</td>
												</tr>
												)
											}
										})
								}
								
								</tbody>
								</table>
							
								{this.state.mode === "listens" &&
									<ul className="pager">
										<li className="previous" className={!this.props.previous_listen_ts ? 'hidden' :''}>
										<a href={`${this.props.profile_url}?min_ts=${this.props.previous_listen_ts}`}>&larr; Previous</a>
										</li>
										<li className="next" disabled={!this.props.next_listen_ts ? 'hidden' : ''}>
										<a href={`${this.props.profile_url}?max_ts=${this.props.next_listen_ts}`}>Next &rarr;</a>
										</li>
									</ul>
								}
						</div>
							
							
						}
					</div>
					<div className="col-md-4" style={{position: "-webkit-sticky",position: "sticky",top: 20}}>
						{ this.props.spotify_access_token ?
							<SpotifyPlayer
								ref={this.spotifyPlayer}
								listens={spotifyListens}
								direction={this.state.mode === "follow" ? "up" : "down"}
								spotify_access_token= {this.props.spotify_access_token}
								onCurrentListenChange={this.handleCurrentListenChange}
								currentListen={this.state.currentListen}
							/> :
							// Fallback embedded player
							<div className="col-md-4 text-right">
								<iframe src={getSpotifyEmbedSrc()} 
									width="300" height="380" frameBorder="0" allowtransparency="true" allow="encrypted-media">
								</iframe>
							</div>
						}
					</div>
				</div>
			</div>);
		}
}

class FollowUsers extends React.Component {
	constructor(props){
		super(props);
		this.state = {
			users: props.initialList || []
		}
		this.addUserToList = this.addUserToList.bind(this);
		this.reorderUser = this.reorderUser.bind(this);
	}

	addUserToList(event){
		event.preventDefault();
		if(this.textInput.value === "" ||
			this.state.users.find(user => user === this.textInput.value)){
			return;
		}
		this.setState(prevState=>{
			return {users: prevState.users.concat([this.textInput.value])}
		},()=>{
			this.textInput.value = "";
			this.props.onUserListChange(this.state.users);
		});
	}
	removeUserFromList(index){
		this.setState(prevState=>{
			prevState.users.splice(index,1);
			return {users: prevState.users}
		},() => {this.props.onUserListChange(this.state.users)});
	}

	reorderUser(currentIndex, targetIndex){
		this.setState(prevState=>{
			var element = prevState.users[currentIndex];
			prevState.users.splice(currentIndex, 1);
			prevState.users.splice(targetIndex, 0, element);
			return {users: prevState.users}
		});
	}

	render(){
		return (
			<div className="panel panel-primary">
				<div className="panel-heading">
					<span style={{fontSize: "x-large"}}>Follow users</span>
				</div>
				<div className="panel-body">
					<div className="text-muted">
					Add a user to discover what they are listening to:
					</div>
					<hr/>
					<div className="input-group">
						<input type="text" className="form-control" placeholder="Username…"
							ref={(input) => this.textInput = input}
						/>
						<span className="input-group-btn btn-primary">
							<button className="btn btn-primary" type="button" onClick={this.addUserToList}>
								<span className="fa fa-plus-circle" aria-hidden="true"></span> Add
							</button>
						</span>
					</div>
					<table className="table table-condensed table-striped">
					<thead>
						<tr>
							<th colSpan="2" width="50px">Order</th>
							<th>User</th>
							<th width="50%">Listening now</th>
							<th width="50px">Remove</th>
							<th width="75px"></th>
						</tr>
					</thead>
					<tbody>
						{this.state.users.map((user,index) => {
							return (
							<tr key={user}>
								<td>
									{index + 1}
								</td>
								<td>
									<span className="btn-group btn-group-xs" role="group" aria-label="Reorder">
										{index > 0 && 
											<button className="btn btn-info"
												onClick={this.reorderUser.bind(this,index,index-1)}>
												<span className="fa fa-chevron-up"></span>
											</button>
										}
										{index < this.state.users.length-1 && 
											<button className="btn btn-info"
												onClick={this.reorderUser.bind(this,index,index+1)}>
												<span className="fa fa-chevron-down"></span>
											</button>
										}
									</span>
								</td>
								<td>
									{user}
								</td>
								<td>
								{this.props.playingNow[user] &&
									<React.Fragment>
										{getTrackLink(this.props.playingNow[user])}
										 <span className="small"> — {getArtistLink(this.props.playingNow[user])}</span>
									</React.Fragment>
								}
								</td>
								<td>
									<button className="btn btn-danger" type="button" aria-label="Remove"
										onClick={this.removeUserFromList.bind(this,index)}>
										<span className="fa fa-trash-alt"></span>
									</button>
								</td>
								<td>
								{this.props.playingNow[user] &&
									getSpotifyPlayButton(this.props.playingNow[user],this.props.playListen)
								}
								</td>
							</tr>
							);
						})}
					</tbody>
					</table>
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
// console.log("props",reactProps);
}
catch(err){
console.error("Error parsing props:", err);
}
ReactDOM.render(<RecentListens {...reactProps}/>, domContainer);
			
window.onSpotifyWebPlaybackSDKReady = window.onSpotifyWebPlaybackSDKReady || console.log; 


