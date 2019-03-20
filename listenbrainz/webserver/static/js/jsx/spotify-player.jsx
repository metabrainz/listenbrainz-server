import {PlaybackControls} from './playback-controls.jsx';
import React from 'react';
import {isEqual as _isEqual} from 'lodash';

function getSpotifyUriFromListen(listen) {
  if (!listen || !listen.track_metadata || !listen.track_metadata.additional_info ||
      typeof listen.track_metadata.additional_info.spotify_id !== "string")
  {
      return null;
  }
  const spotifyId = listen.track_metadata.additional_info.spotify_id;
  const spotify_track = spotifyId.split('https://open.spotify.com/')[1];
  if (typeof spotify_track !== "string")
  {
      return null;
  }
  return "spotify:" + spotify_track.replace("/", ":");
}

export class SpotifyPlayer extends React.Component {

  _spotifyPlayer;
  _firstRun = true;
  _playerStateTimerID = null;

  constructor(props) {
    super(props);
    this.state = {
      accessToken: props.spotify_user.access_token,
      permission: props.spotify_user.permission,
      currentSpotifyTrack: {},
      playerPaused: true,
      progressMs: 0,
      durationMs: 0,
      direction: props.direction || "down"
    };

    this.connectSpotifyPlayer = this.connectSpotifyPlayer.bind(this);
    this.disconnectSpotifyPlayer = this.disconnectSpotifyPlayer.bind(this);
    this.getAlbumArt = this.getAlbumArt.bind(this);
    this.handleError = this.handleError.bind(this);
    this.handlePlayerStateChanged = this.handlePlayerStateChanged.bind(this);
    this.handleSpotifyAPICurrentlyPlaying = this.handleSpotifyAPICurrentlyPlaying.bind(this);
    this.handleTokenError = this.handleTokenError.bind(this);
    this.isCurrentListen = this.isCurrentListen.bind(this);
    this.playListen = this.playListen.bind(this);
    this.playNextTrack = this.playNextTrack.bind(this);
    this.debouncedPlayNextTrack = _.debounce(this.playNextTrack, 500, {leading:true, trailing:false});
    this.playPreviousTrack = this.playPreviousTrack.bind(this);
    this.startPlayerStateTimer = this.startPlayerStateTimer.bind(this);
    this.stopPlayerStateTimer = this.stopPlayerStateTimer.bind(this);
    this.togglePlay = this.togglePlay.bind(this);
    this.toggleDirection = this.toggleDirection.bind(this);
    // Do an initial check of the spotify token permissions (scopes) before loading the SDK library
    this.checkSpotifyToken(this.state.accessToken, this.state.permission).then(success => {
      if(success){
        window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer;
        const spotifyPlayerSDKLib = require('../lib/spotify-player-sdk-1.6.0');
      }
    })
    // ONLY FOR TESTING PURPOSES
    window.disconnectSpotifyPlayer = this.disconnectSpotifyPlayer;
  }

  componentWillUnmount() {
    this.disconnectSpotifyPlayer();
  }

  play_spotify_uri(spotify_uri) {
    if (!this._spotifyPlayer)
    {
      return this.connectSpotifyPlayer(this.play_spotify_uri.bind(this, spotify_uri));
    }
    fetch(`https://api.spotify.com/v1/me/player/play?device_id=${this._spotifyPlayer._options.id}`, {
      method: 'PUT',
      body: JSON.stringify({ uris: [spotify_uri] }),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.state.accessToken}`
      },
    })
    .then(response =>{
      if(response.status === 401){
        return this.handleTokenError(response.statusText, this.play_spotify_uri.bind(this, spotify_uri));
      }
      if(response.status === 403){
        return this.handleAccountError(response.statusText);
      }
      if(response.status === 404){ 
        // Device not found
        return this.connectSpotifyPlayer(this.play_spotify_uri.bind(this, spotify_uri));
      }
      if(!response.ok){
        return this.handleError(response.statusText);
      }
      return;
    })
    .catch(this.handleError);
  };

  async checkSpotifyToken(accessToken, permission){

    if(!accessToken || !permission){
      this.handleAccountError(noTokenErrorMessage);
      return false;
    }
    try {
      const scopes = permission.split(" ");
      const requiredScopes = ["streaming", "user-read-birthdate", "user-read-email", "user-read-private"];
      for (var i in requiredScopes) {
        if (!scopes.includes(requiredScopes[i])) {
          if(typeof this.props.onPermissionError === "function") {
            this.props.onPermissionError("Permission to play songs not granted");
          }
          return false;
        }
      }
      return true;

    } catch (error) {
      this.handleError(error);
      return false;
    }

  }

  playListen(listen) {
    if (listen.track_metadata.additional_info.spotify_id)
    {
      this.play_spotify_uri(getSpotifyUriFromListen(listen));
      this.props.onCurrentListenChange(listen);
    } else
    {
      this.handleWarning("This song was not listened to on Spotify", "Cannot play this song");
    }
  };
  isCurrentListen(element) {
    return this.props.currentListen
      && _isEqual(element,this.props.currentListen);
  }
  playPreviousTrack() {
    this.playNextTrack(true);
  }
  playNextTrack(invert) {
    if (this.props.listens.length === 0)
    {
      this.handleWarning("You can try loading listens or refreshing the page", "No Spotify listens to play");
      return;
    }

    const currentListenIndex = this.props.listens.findIndex(this.isCurrentListen);

    let nextListenIndex;
    if (currentListenIndex === -1)
    {
      nextListenIndex = this.state.direction === "up" ? this.props.listens.length - 1 : 0;
    }
    else if (this.state.direction === "up")
    {
      nextListenIndex = invert === true ? currentListenIndex + 1 : (currentListenIndex - 1 || 0);
    }
    else if (this.state.direction === "down")
    {
      nextListenIndex = invert === true ? (currentListenIndex - 1 || 0) : currentListenIndex + 1;
    }
    else {
      this.handleWarning("Please select a song to play","Unrecognised state")
      return;
    }
    
    const nextListen = this.props.listens[nextListenIndex];
    if (!nextListen)
    {
      this.handleWarning("You can try loading more listens or refreshing the page","No more Spotify listens to play");
      return;
    }

    this.playListen(nextListen);
  }
  handleError(error, title) {
    if (!error)
    {
      return;
    }
    console.error(error);
    error = error.message ? error.message : error;
    this.props.newAlert('danger', title || 'Playback error', error);
  }

  handleWarning(message, title) {
    console.debug(message);
    this.props.newAlert('warning', title || 'Playback error', message);
  }

  async handleTokenError(error, callbackFunction) {
    console.error(error);
    if(error && error.message === "Invalid token scopes.") {
      this.handleAccountError(error.message)
    }
    try {
      const userToken = await this.props.APIService.refreshSpotifyToken();
      this.setState({accessToken: userToken},()=>{
        this.connectSpotifyPlayer(callbackFunction);
      });
    } catch (err) {
      this.handleError(err);
    }
    return;
  }

  handleAccountError(error) {
    const errorMessage = <p>In order to play music, it is required that you link your Spotify Premium account.<br/>Please try to <a href="/profile/connect-spotify" target="_blank">link for "playing music" feature</a> and refresh this page</p>;
    console.error('Failed to validate Spotify account', error);
    if(typeof this.props.onAccountError === "function") {
      this.props.onAccountError(errorMessage);
    }
  }

  async togglePlay() {
    try
    {
      await this._spotifyPlayer.togglePlay();
    } catch (error)
    {
      this.handleError(error);
    }
  }

  toggleDirection() {
    this.setState(prevState => {
      const direction = prevState.direction === "down" ? "up" : "down";
      return { direction: direction }
    });
  }
  disconnectSpotifyPlayer() {
    this.stopPlayerStateTimer();
    if (!this._spotifyPlayer)
    {
      return;
    }
    if (typeof this._spotifyPlayer.disconnect === "function")
    {
      this._spotifyPlayer.removeListener('initialization_error');
      this._spotifyPlayer.removeListener('authentication_error');
      this._spotifyPlayer.removeListener('account_error');
      this._spotifyPlayer.removeListener('playback_error');
      this._spotifyPlayer.removeListener('ready');
      this._spotifyPlayer.removeListener('player_state_changed');
      this._spotifyPlayer.disconnect();
    }
    this._spotifyPlayer = null;
    this._firstRun = true;
  }

  connectSpotifyPlayer(callbackFunction) {
    this.disconnectSpotifyPlayer();

    this._spotifyPlayer = new window.Spotify.Player({
      name: 'ListenBrainz Player',
      getOAuthToken: authCallback => {
        authCallback(this.state.accessToken);
      },
      volume: 0.7 // Careful with this, now…
    });

    // Error handling
    this._spotifyPlayer.on('initialization_error', this.handleError);
    this._spotifyPlayer.on('authentication_error', this.handleTokenError);
    this._spotifyPlayer.on('account_error', this.handleAccountError);
    this._spotifyPlayer.on('playback_error', this.handleError);

    this._spotifyPlayer.addListener('ready', ({ device_id }) => {
      console.debug('Spotify player connected with Device ID', device_id);
      if(callbackFunction){
        callbackFunction();
      }
      this.startPlayerStateTimer()
    });

    this._spotifyPlayer.addListener('player_state_changed', this.handlePlayerStateChanged);

    this._spotifyPlayer.connect().then(success => {
      if (success)
      {
        console.debug('The Web Playback SDK successfully connected to Spotify!');
        return fetch('https://api.spotify.com/v1/me/player/currently-playing', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.state.accessToken}`
          },
        });
      }
      else
      {
        throw Error('Could not connect Web Playback SDK');
      }
    })
    .then(response => {
      if(response.status === 202 || response.status === 204)
      {
        // Failure, no response body.
        return;
      }
      return response.json().then(response => {
        if (response.error) {
          return this.handleError(response.error)
        }
        this.handleSpotifyAPICurrentlyPlaying(response);
      })
    })
    .catch(this.handleError);
  }

  handleSpotifyAPICurrentlyPlaying(currentlyPlaying) {
    if(currentlyPlaying.is_playing){
      this.handleWarning('Using Spotify on this page will interrupt your current playback', "Spotify player");
    }
    this.setState({
      progressMs: currentlyPlaying.progress_ms,
      durationMs: currentlyPlaying.item && currentlyPlaying.item.duration_ms,
      currentSpotifyTrack: currentlyPlaying.item,
    });
  }

  startPlayerStateTimer() {
    this._playerStateTimerID = setInterval(()=>{
      this._spotifyPlayer.getCurrentState().then(this.handlePlayerStateChanged)
    }, 500);
  }
  stopPlayerStateTimer() {
    clearInterval(this._playerStateTimerID);
    this._playerStateTimerID = null;
  }
  handlePlayerStateChanged(state) {
    if(!state) {
      return;
    }
    const {
      paused,
      position,
      duration,
      track_window: { current_track }
    } = state;

    if(paused) {
      this.stopPlayerStateTimer();
    } else if (!this._playerStateTimerID){
      this.startPlayerStateTimer();
    }
    // How do we accurately detect the end of a song?
    // From https://github.com/spotify/web-playback-sdk/issues/35#issuecomment-469834686
    if (position === 0 && paused === true &&
      _.has(state, "restrictions.disallow_resuming_reasons") && state.restrictions.disallow_resuming_reasons[0] === "not_paused")
    {
      // Track finished, play next track
      console.debug("Detected Spotify end of track, playing next track");
      console.debug('Spotify player state', state);
      this.debouncedPlayNextTrack();
      return;
    }
    this.setState({
      progressMs: position,
      durationMs: duration,
      currentSpotifyTrack: current_track || {},
      playerPaused: paused
    });
    if (this._firstRun)
    {
      this._firstRun = false;
    }
  }

  getAlbumArt() {
    const track = this.state.currentSpotifyTrack;
    if (!track || !track.album || !Array.isArray(track.album.images))
    {
      return null
    }
    const sortedImages = track.album.images.sort((a, b) => a.height > b.height ? -1 : 1);
    return sortedImages[0] && <img className="img-responsive" src={sortedImages[0].url} />;
  }

  render() {
    return (
      <div>
        <PlaybackControls
          playPreviousTrack={this.playPreviousTrack}
          playNextTrack={this.playNextTrack}
          togglePlay={this._firstRun ? this.playNextTrack : this.togglePlay}
          playerPaused={this.state.playerPaused}
          toggleDirection={this.toggleDirection}
          direction={this.state.direction}
          trackName={this.state.currentSpotifyTrack.name}
          artistName={this.state.currentSpotifyTrack.artists &&
            this.state.currentSpotifyTrack.artists.map(artist => artist.name).join(', ')
          }
          progress_ms={this.state.progressMs}
          duration_ms={this.state.durationMs}
        >
          {this.getAlbumArt()}
        </PlaybackControls>
      </div>
    );
  }
}
